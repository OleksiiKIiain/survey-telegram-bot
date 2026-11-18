// Browser regression tests with in-memory API fixtures; never writes to the database.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core');
const base = process.env.FRONTEND_URL || 'http://localhost:5173';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function eventually(check, message, timeout = 12000) {
  const deadline = Date.now() + timeout;
  do {
    if (await check()) return;
    await sleep(100);
  } while (Date.now() < deadline);
  throw new Error(message);
}

async function fixture(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript(() => {
    localStorage.setItem('token', 'local-browser-test');
    localStorage.setItem('lang', 'uk');
    window.__pageIdentity = Math.random();
  });
  const page = await context.newPage();
  const state = { version: 1, fail: false, delay: 0, requests: [], errors: [] };
  page.on('pageerror', error => state.errors.push(error.message));
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    const surveyId = url.searchParams.get('survey_id') || '1';
    const version = state.version;
    const fail = state.fail;
    state.requests.push(url.pathname + url.search);
    if (url.pathname.endsWith('/surveys')) {
      return route.fulfill({ json: [1, 2].map(id => ({
        id, title: `Survey ${id}`, title_uk: `Survey ${id}`, status: 'active',
        created_at: '2026-11-17T10:00:00Z', updated_at: '2026-11-17T10:00:00Z'
      })) });
    }
    if (state.delay && surveyId === '1') await sleep(state.delay);
    if (fail) return route.fulfill({ status: 503, json: { detail: 'Temporary test outage' } });
    if (url.pathname.endsWith('/responses/answers')) {
      return route.fulfill({ json: Array.from({ length: version }, (_, i) => ({
        id: Number(surveyId) * 100 + i, session_id: i + 1, question_id: Number(surveyId),
        text_value: `Survey ${surveyId} response ${i + 1}`, number_value: null,
        question_text: `Question ${surveyId}`, created_at: '2026-11-17T10:00:00Z'
      })) });
    }
    if (url.pathname.endsWith('/analytics/overview')) {
      return route.fulfill({ json: {
        total_respondents: version, total_sessions: version, completed_sessions: version,
        unfinished_sessions: 0, active_surveys: 2,
        sessions_by_status: [{ name: 'completed', value: version }],
        recent_sessions: [{ session_id: version, survey_title: 'Survey 1',
          respondent: `Test ${version}`, status: 'completed', started_at: '2026-11-17T10:00:00Z' }],
        question_stats: [{ question_id: 1, question_text: `Question ${surveyId}`,
          question_type: 'scale', total_answers: version + 1,
          distribution: [{ name: '1', value: 1 }, { name: '2', value: version }],
          average: 1.5, text_answers: [] }]
      } });
    }
    throw new Error(`Unexpected API request: ${url.pathname}`);
  });
  return { page, state, context };
}

async function responsesTest(browser) {
  const { page, state, context } = await fixture(browser);
  try {
    await page.goto(base + '/responses?survey_id=1');
    await page.getByText('Survey 1 response 1', { exact: true }).waitFor();
    assert.equal(await page.locator('main select').inputValue(), '1', 'Read the shared survey filter from the URL');
    await page.locator('main select').selectOption('1');
    await page.waitForLoadState('networkidle');
    const identity = await page.evaluate(() => window.__pageIdentity);
    state.version = 2;
    await page.getByText('Survey 1 response 2', { exact: true }).waitFor({ timeout: 12000 });
    assert.equal(await page.locator('main select').inputValue(), '1');
    assert.equal(await page.evaluate(() => window.__pageIdentity), identity);
    state.fail = true;
    await page.getByRole('status').waitFor({ timeout: 12000 });
    assert.equal(await page.locator('tbody tr').count(), 2, 'Keep last data during an outage');
    state.fail = false;
    state.version = 3;
    await page.getByText('Survey 1 response 3', { exact: true }).waitFor({ timeout: 12000 });
    assert.equal(await page.getByRole('status').count(), 0);

    // A slow response from an old filter must not replace the new filter's data.
    state.delay = 1800;
    await page.locator('main select').selectOption('2');
    await page.getByText('Survey 2 response 3', { exact: true }).waitFor();
    const requestCount = state.requests.length;
    await page.locator('main select').selectOption('1');
    await eventually(() => state.requests.length > requestCount, 'Old filter request started');
    await page.locator('main select').selectOption('2');
    await page.getByText('Survey 2 response 3', { exact: true }).waitFor();
    await sleep(2200);
    assert.equal(await page.getByText('Survey 1 response 3', { exact: true }).count(), 0);
    assert.equal(await page.locator('main select').inputValue(), '2');
    assert.equal(new URL(page.url()).searchParams.get('survey_id'), '2');
    await page.getByRole('link', { name: 'Опитування', exact: true }).click();
    await page.waitForLoadState('networkidle');
    const stoppedCount = state.requests.filter(p => p.includes('/responses/answers')).length;
    await sleep(5500);
    assert.equal(state.requests.filter(p => p.includes('/responses/answers')).length, stoppedCount,
      'Stop polling after leaving Responses');
    assert.deepEqual(state.errors, []);
    console.log('PASS responses: automatic rows, preserved filter, outage/retry, stale request, cleanup');
  } finally { await context.close(); }
}

async function analyticsTest(browser) {
  const { page, state, context } = await fixture(browser);
  try {
    await page.goto(base + '/analytics?survey_id=1');
    await page.locator('main select').selectOption('1');
    assert.equal(new URL(page.url()).searchParams.get('survey_id'), '1');
    await page.locator('section h2').waitFor();
    await sleep(1200);
    const before = await page.locator('.recharts-bar-rectangle path').evaluateAll(nodes =>
      nodes.map(node => node.getAttribute('height')));
    const identity = await page.evaluate(() => window.__pageIdentity);
    state.version = 2;
    await eventually(async () => (await page.locator('section').innerText()).includes('3 відповідей'),
      'Question answer total updates automatically');
    await sleep(1200);
    const after = await page.locator('.recharts-bar-rectangle path').evaluateAll(nodes =>
      nodes.map(node => node.getAttribute('height')));
    assert.notDeepEqual(after, before, 'Chart bars update with the new distribution');
    assert.equal(await page.locator('main .text-3xl').first().innerText(), '2');
    assert.equal(await page.locator('main select').inputValue(), '1');
    assert.equal(await page.evaluate(() => window.__pageIdentity), identity);
    assert.deepEqual(state.errors, []);
    console.log('PASS analytics: automatic counters, answer totals, SVG bar geometry, no reload');
  } finally { await context.close(); }
}

async function dashboardTest(browser) {
  const { page, state, context } = await fixture(browser);
  try {
    state.fail = true;
    await page.goto(base + '/');
    await page.getByRole('status').waitFor();
    state.fail = false;
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await page.locator('main .text-3xl').first().waitFor();
    state.version = 2;
    await eventually(async () => await page.locator('main .text-3xl').first().innerText() === '2',
      'Dashboard updates automatically');
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await page.waitForLoadState('networkidle');
    const hiddenCount = state.requests.length;
    state.version = 3;
    await sleep(5500);
    assert.equal(state.requests.length, hiddenCount, 'Hidden tab does not poll');
    await page.evaluate(() => {
      Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await eventually(async () => await page.locator('main .text-3xl').first().innerText() === '3',
      'Returning to tab refreshes immediately', 3000);
    assert.deepEqual(state.errors, []);
    console.log('PASS dashboard: initial failure recovery, live totals, pause hidden, resume immediately');
  } finally { await context.close(); }
}

async function main() {
  const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || 'msedge', headless: true });
  try {
    await responsesTest(browser);
    await analyticsTest(browser);
    await dashboardTest(browser);
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
