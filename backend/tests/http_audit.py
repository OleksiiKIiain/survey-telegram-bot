"""Real HTTP smoke tests; start only against an isolated audit database."""
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from openpyxl import load_workbook

BASE = os.environ.get('AUDIT_API_URL', 'http://127.0.0.1:8000')
if 'survey_audit_' not in os.environ.get('DATABASE_URL', ''):
    raise RuntimeError('A dedicated audit database is required')
results = []
token = ''
bot_key = hashlib.sha256(os.environ['TELEGRAM_BOT_TOKEN'].encode()).hexdigest()


def request(method, path, payload=None, admin=False, bot=False):
    headers = {'Content-Type': 'application/json'}
    if admin:
        headers['Authorization'] = 'Bearer ' + token
    if bot:
        headers['X-Bot-Key'] = bot_key
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            return response.status, data
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def check(name, actual, expected):
    passed = actual == expected
    results.append({'test': name, 'passed': passed, 'actual': actual, 'expected': expected})
    if not passed:
        raise AssertionError(results[-1])


def data(method, path, payload=None, admin=False, bot=False):
    status, raw = request(method, path, payload, admin, bot)
    if status >= 400:
        raise RuntimeError((path, status, raw.decode()))
    return json.loads(raw)


check('health', request('GET', '/health')[0], 200)
check('admin_without_jwt', request('GET', '/api/v1/surveys')[0], 401)
check('bot_without_key', request('GET', '/api/v1/public/surveys')[0], 401)
check('invalid_login', request('POST', '/api/v1/auth/login', {'email': 'admin@example.com', 'password': 'wrong'})[0], 401)
token = data('POST', '/api/v1/auth/login', {'email': 'admin@example.com', 'password': 'admin12345'})['access_token']
check('valid_login', bool(token), True)
survey = data('POST', '/api/v1/surveys', {'title': 'Аудит HTTP', 'title_uk': 'Аудит HTTP', 'title_en': 'HTTP audit', 'status': 'active', 'questions': [
    {'text': 'Вибір', 'text_uk': 'Вибір', 'text_en': 'Choice', 'type': 'single_choice', 'position': 0, 'options': [{'text': 'Так', 'text_uk': 'Так', 'text_en': 'Yes'}, {'text': 'Ні', 'text_uk': 'Ні', 'text_en': 'No'}]},
    {'text': 'Кілька', 'type': 'multiple_choice', 'position': 1, 'options': [{'text': 'A'}, {'text': 'B'}]},
    {'text': 'Коментар', 'type': 'free_text', 'position': 2},
    {'text': 'Оцінка', 'type': 'scale', 'scale_min': 0, 'scale_max': 5, 'position': 3},
]}, admin=True)
sid = survey['id']
user = data('POST', '/api/v1/public/respondents', {'telegram_id': 990000000000 + sid, 'first_name': 'Audit'}, bot=True)
session = data('POST', '/api/v1/public/sessions', {'survey_id': sid, 'respondent_id': user['id']}, bot=True)['session']['id']
check('incomplete_session_rejected', request('POST', f'/api/v1/public/sessions/{session}/complete', bot=True)[0], 422)
qs = survey['questions']
for question, value in zip(qs, [{'option_id': qs[0]['options'][0]['id']}, {'option_ids': [qs[1]['options'][0]['id'], qs[1]['options'][1]['id']]}, {'text_value': '=1+1'}, {'number_value': 0}]):
    check('save_' + question['type'], request('POST', f'/api/v1/public/sessions/{session}/answers', {'question_id': question['id'], **value}, bot=True)[0], 201)
check('complete', data('POST', f'/api/v1/public/sessions/{session}/complete', bot=True)['status'], 'completed')
check('completed_session_is_immutable', request('POST', f'/api/v1/public/sessions/{session}/answers', {'question_id': qs[3]['id'], 'number_value': 4}, bot=True)[0], 400)
old_ids = [option['id'] for option in qs[0]['options']]
updated = data('PATCH', f'/api/v1/surveys/{sid}/questions/{qs[0]["id"]}', {'text_en': 'Edited choice', 'options': qs[0]['options']}, admin=True)
check('preserve_option_ids', [option['id'] for option in updated['options']], old_ids)
check('translation_persists', data('GET', f'/api/v1/surveys/{sid}', admin=True)['questions'][0]['text_en'], 'Edited choice')
stats = data('GET', f'/api/v1/analytics/overview?survey_id={sid}', admin=True)
check('analytics_completed', stats['completed_sessions'], 1)
check('analytics_scale_zero', stats['question_stats'][3]['average'], 0.0)
check('analytics_single_count', stats['question_stats'][0]['distribution'][0]['value'], 1)
check('analytics_multiple_count', sum(item['value'] for item in stats['question_stats'][1]['distribution']), 2)
status, raw = request('GET', f'/api/v1/export/surveys/{sid}.csv', admin=True)
rows = list(csv.reader(io.StringIO(raw.decode())))
check('csv_rows', len(rows), 5)
check('csv_formula_escaped', any(row[3] == "'=1+1" for row in rows[1:]), True)
status, raw = request('GET', f'/api/v1/export/surveys/{sid}.xlsx', admin=True)
workbook = load_workbook(io.BytesIO(raw), data_only=False)
check('xlsx_rows', workbook.active.max_row, 5)
check('xlsx_no_formulas', any(cell.data_type == 'f' for row in workbook.active for cell in row), False)
cancelled = data('POST', '/api/v1/public/sessions', {'survey_id': sid, 'respondent_id': user['id']}, bot=True)['session']['id']
check('cancel', data('POST', f'/api/v1/public/sessions/{cancelled}/cancel', bot=True)['status'], 'cancelled')
check('cancelled_complete_rejected', request('POST', f'/api/v1/public/sessions/{cancelled}/complete', bot=True)[0], 409)
translation_status, translated = request('POST', '/api/v1/translate', {'text': 'Оберіть відповідь', 'source_lang': 'uk', 'target_lang': 'en'}, admin=True)
translation = {'http_status': translation_status}
if translation_status == 200:
    translation['output'] = json.loads(translated)['translated_text']


def timed_request(_):
    start = time.perf_counter()
    status, _ = request('GET', f'/api/v1/analytics/overview?survey_id={sid}', admin=True)
    return status, (time.perf_counter() - start) * 1000


start = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    samples = list(pool.map(timed_request, range(80)))
elapsed = time.perf_counter() - start
durations = sorted(sample[1] for sample in samples)
load = {'requests': 80, 'workers': 8, 'errors': sum(code != 200 for code, _ in samples), 'elapsed_seconds': round(elapsed, 3),
        'median_ms': round(statistics.median(durations), 2), 'p95_ms': round(durations[int(0.95 * len(durations)) - 1], 2), 'throughput_rps': round(80 / elapsed, 2),
        'scope': 'HTTP analytics on a small isolated dataset, not a production capacity benchmark'}
check('delete_test_survey', request('DELETE', f'/api/v1/surveys/{sid}', admin=True)[0], 204)
report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Real HTTP + PostgreSQL, no Telegram client E2E', 'results': results, 'translation': translation, 'load': load}
with open('/tmp/http_audit.json', 'w', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
