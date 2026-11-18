"""Compare logical rows of the audit database and its separately restored copy."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import psycopg

names = [os.environ.get('AUDIT_SOURCE_DATABASE', 'survey_audit_review_20261118'),
         os.environ.get('AUDIT_RESTORE_DATABASE', 'survey_audit_restore_20261118')]
tables = ['admins', 'telegram_users', 'surveys', 'questions', 'question_options', 'survey_sessions', 'answers', 'audit_logs', 'alembic_version']
def snapshot(name):
    assert name.startswith('survey_audit_')
    result = {}
    with psycopg.connect(host='db', user='survey_user', password='survey_password', dbname=name) as db:
        for table in tables:
            with db.cursor() as cursor:
                cursor.execute('SELECT row_to_json(t)::text FROM ' + table + ' t ORDER BY 1')
                rows = [row[0] for row in cursor.fetchall()]
            result[table] = {'count': len(rows), 'sha256': hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
    return result
before, restored = map(snapshot, names)
assert before == restored, 'The restored logical rows differ'
report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'source': names[0], 'restored': names[1],
          'matched': True, 'tables': before, 'format': 'pg_dump custom / pg_restore, separate empty database',
          'boundary': 'Audit data only. Does not prove production RPO/RTO, secrets recovery, or bot FSM restoration.'}
Path('/evidence/backup-restore.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
