"""Three bounded real HTTP read-load runs against the dedicated audit API."""
import concurrent.futures
import json
import os
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if 'survey_audit_' not in os.environ.get('DATABASE_URL', ''):
    raise RuntimeError('A dedicated audit database is required')
BASE = 'http://127.0.0.1:8000/api/v1'
req = urllib.request.Request(BASE + '/auth/login', data=json.dumps({'email': 'admin@example.com', 'password': 'admin12345'}).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10) as response:
    token = json.load(response)['access_token']

def sample(_):
    started = time.perf_counter()
    req = urllib.request.Request(BASE + '/analytics/overview?survey_id=1', headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            code = response.status
    except Exception:
        code = 0
    return code, 1000 * (time.perf_counter() - started)

for _ in range(5):
    sample(None)
runs = []
for run in range(3):
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        samples = list(pool.map(sample, range(80)))
    elapsed = time.perf_counter() - started
    durations = sorted(row[1] for row in samples)
    runs.append({'run': run + 1, 'requests': 80, 'workers': 8, 'errors': sum(code != 200 for code, _ in samples),
                 'median_ms': round(statistics.median(durations), 2), 'p95_ms': round(durations[75], 2),
                 'elapsed_seconds': round(elapsed, 3), 'throughput_rps': round(80 / elapsed, 2)})
report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'endpoint': 'GET /api/v1/analytics/overview?survey_id=1',
          'dataset': 'Unmodified seeded survey 1 in dedicated audit database', 'warmup_requests': 5,
          'client': 'urllib + ThreadPoolExecutor inside the isolated API container, no TLS', 'runs': runs,
          'scope': 'Small read-only dataset, shared Docker Desktop host; not production capacity or Telegram latency'}
Path('/evidence/repeat-load.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
