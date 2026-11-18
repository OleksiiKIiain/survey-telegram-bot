"""Verify real, authenticated translation HTTP requests using non-private text."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('AUDIT_TRANSLATION_URL', 'http://localhost:8000/api/v1')

def request(path, payload, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.status, json.load(response)

_, login = request('/auth/login', {'email': os.environ.get('DEMO_ADMIN_EMAIL', 'admin@example.com'),
                                  'password': os.environ.get('DEMO_ADMIN_PASSWORD', 'admin12345')})
cases = [('en', 'uk', 'Survey about the quality of education'),
         ('uk', 'en', 'Як ви оцінюєте якість навчання?'),
         ('uk', 'en', 'Так\n\nНі')]
results = []
for source, target, text in cases:
    status, result = request('/translate', {'text': text, 'source_lang': source, 'target_lang': target}, login['access_token'])
    translated = result['translated_text']
    assert status == 200 and translated.strip() and translated != text
    assert bool(re.search('[А-Яа-яІіЇїЄє]', translated)) == (target == 'uk')
    if '\n\n' in text:
        assert '\n\n' in translated
    results.append({'source': source, 'target': target, 'text': text, 'translated_text': translated, 'http_status': status})
report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'provider': 'MyMemory',
          'method': 'Real authenticated POST /api/v1/translate; no mocks; generic test phrases only',
          'results': results, 'boundary': 'Confirms these requests and language directions, not general translation quality or availability.'}
destination = ROOT/'docs/thesis/evidence/translation-live-20261118.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
