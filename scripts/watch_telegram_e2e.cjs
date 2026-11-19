// Real API and visible-page polling only. This script never sends Telegram messages.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core');
const root = path.resolve(__dirname, '..');
const originalOut = path.join(root, 'output/thesis/closeout-20261118/e2e');
const out = process.env.E2E_OUT_DIR ? path.resolve(process.env.E2E_OUT_DIR) : originalOut;
fs.mkdirSync(out, { recursive: true });
const statePath = path.join(originalOut, 'state.json');
const title = 'Контрольний показ 18.11';
const comment = 'Перевірка для магістерської 18.11';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function trackDocuments(page) {
  const state = { requests: 0, frameEvents: 0 };
  page.on('request', request => {
    if (request.isNavigationRequest() && request.resourceType() === 'document' && request.frame() === page.mainFrame()) state.requests++;
  });
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) state.frameEvents++; });
  return state;
}

async function navigationSelfTest(browser) {
  const page = await browser.newPage();
  await page.route('http://localhost/navigation-test**', route => route.fulfill({ contentType: 'text/html', body: '<title>Navigation control</title>' }));
  const state = trackDocuments(page);
  await page.goto('http://localhost/navigation-test');
  await page.evaluate(() => { window.testIdentity = 'unchanged'; history.replaceState({}, '', '?filter=1'); history.pushState({}, '', '?filter=2'); });
  assert.equal(state.requests, 1);
  assert.equal(await page.evaluate(() => window.testIdentity), 'unchanged');
  assert.ok(state.frameEvents >= 2);
  await page.reload();
  assert.equal(state.requests, 2);
  assert.equal(await page.evaluate(() => window.testIdentity), undefined);
  console.log(JSON.stringify({ navigation_self_test: 'passed', document_requests: state.requests, frame_events: state.frameEvents, browser_version: browser.version(), node_version: process.version, playwright_version: require((process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core') + '/package.json').version }));
}

async function main() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    if (process.argv.includes('--navigation-self-test')) return await navigationSelfTest(browser);
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const login = await context.request.post('http://localhost:8000/api/v1/auth/login', {
      data: { email: 'admin@example.com', password: 'admin12345' }
    });
    assert.equal(login.status(), 200);
    const token = (await login.json()).access_token;
    const headers = { Authorization: 'Bearer ' + token };
    let survey;
    if (fs.existsSync(statePath)) {
      const stored = JSON.parse(fs.readFileSync(statePath, 'utf8'));
      const response = await context.request.get(`http://localhost:8000/api/v1/surveys/${stored.survey_id}`, { headers });
      assert.equal(response.status(), 200);
      survey = await response.json();
    } else {
      const option = (uk, en, position) => ({ text: uk, text_uk: uk, text_en: en, position });
      const question = (uk, en, type, position, extra = {}) => ({ text: uk, text_uk: uk, text_en: en, type, position, is_required: true, ...extra });
      const response = await context.request.post('http://localhost:8000/api/v1/surveys', { headers, data: {
        title, title_uk: title, title_en: 'Controlled demonstration 18.11', status: 'active',
        description: 'Контрольне проходження для перевірки магістерської, не соціологічні дані.',
        description_uk: 'Контрольне проходження для перевірки магістерської, не соціологічні дані.',
        description_en: 'A controlled thesis verification, not sociological research.',
        questions: [
          question('Оцініть зручність опитування.', 'Rate the survey experience.', 'scale', 0, { scale_min: 1, scale_max: 5 }),
          question('Як ви відкрили опитування?', 'How did you open the survey?', 'single_choice', 1, { options: [option('Через меню бота', 'Using the bot menu', 0), option('Командою /surveys', 'Using /surveys', 1)] }),
          question('Які частини системи ви перевірили?', 'Which parts did you verify?', 'multiple_choice', 2, { options: [option('Telegram-бот', 'Telegram bot', 0), option('Адмін-панель', 'Admin panel', 1), option('Графіки', 'Charts', 2)] }),
          question('Залиште тестовий коментар.', 'Leave a test comment.', 'free_text', 3)
        ]
      } });
      assert.equal(response.status(), 201);
      survey = await response.json();
      fs.writeFileSync(statePath, JSON.stringify({ survey_id: survey.id, title, comment }, null, 2));
    }
    await context.addInitScript(({ token }) => { localStorage.setItem('token', token); localStorage.setItem('lang', 'uk'); }, { token });
    if (process.argv.includes('--prepare')) {
      const page = await context.newPage();
      await page.goto(`http://localhost:5173/surveys/${survey.id}`);
      await page.getByText(title, { exact: true }).first().waitFor();
      await page.screenshot({ path: path.join(out, 'survey.png'), fullPage: true });
      await page.goto(`http://localhost:5173/surveys/${survey.id}/edit`);
      await page.getByText('Питання UA', { exact: true }).first().waitFor();
      await page.screenshot({ path: path.join(out, 'editor.png'), fullPage: true });
      console.log(JSON.stringify({ survey_id: survey.id, title }));
      return;
    }
    const responses = await context.newPage();
    const analytics = await context.newPage();
    const errors = [];
    const navigation = { responses: trackDocuments(responses), analytics: trackDocuments(analytics) };
    const polls = { responses: 0, analytics: 0 };
    let latestStats;
    for (const [name, page] of [['responses', responses], ['analytics', analytics]]) {
      page.on('pageerror', e => errors.push(e.message));
      page.on('response', async response => {
        if (response.url().includes(name === 'responses' ? '/responses/answers?' : '/analytics/overview?')) {
          polls[name]++;
          if (name === 'analytics' && response.ok()) latestStats = await response.json();
        }
      });
      await page.goto(`http://localhost:5173/${name}?survey_id=${survey.id}`);
      await page.locator('main select').first().waitFor();
      await page.evaluate(() => { window.__e2eIdentity = crypto.randomUUID(); });
    }
    const initialAnswersResponse = await context.request.get(`http://localhost:8000/api/v1/responses/answers?survey_id=${survey.id}`, { headers });
    assert.equal(initialAnswersResponse.status(), 200);
    const initialAnswers = await initialAnswersResponse.json();
    const initialDeadline = Date.now() + 15000;
    while ((!latestStats || await responses.locator('tbody tr').count() !== initialAnswers.length) && Date.now() < initialDeadline) await sleep(100);
    assert.ok(latestStats, 'Initial analytics response loaded');
    const before = { rows: await responses.locator('tbody tr').count(), comment_count: await responses.getByText(comment, { exact: true }).count(), completed: latestStats.completed_sessions,
      stats: latestStats.question_stats.map(q => ({ id: q.question_id, total: q.total_answers, average: q.average, distribution: q.distribution })),
      identities: [await responses.evaluate(() => window.__e2eIdentity), await analytics.evaluate(() => window.__e2eIdentity)] };
    assert.equal(before.rows, initialAnswers.length);
    await responses.screenshot({ path: path.join(out, 'responses-before.png'), fullPage: true });
    await analytics.screenshot({ path: path.join(out, 'analytics-before.png'), fullPage: true });
    fs.writeFileSync(path.join(out, 'ready.json'), JSON.stringify({ survey_id: survey.id, before, started_utc: new Date().toISOString() }, null, 2));
    console.log('Observation ready for survey ' + survey.id + '; no page reloads will be performed.');
    const deadline = Date.now() + 20 * 60 * 1000;
    while (Date.now() < deadline) {
      if (await responses.getByText(comment, { exact: true }).count() === before.comment_count + 1 && latestStats?.completed_sessions === before.completed + 1) break;
      await sleep(1000);
    }
    assert.ok(Date.now() < deadline, 'No completed real Telegram session observed within 20 minutes');
    await sleep(1800);
    assert.equal(await responses.locator('tbody tr').count(), before.rows + 4);
    assert.equal(await responses.getByText(comment, { exact: true }).count(), before.comment_count + 1);
    assert.ok(latestStats.question_stats.every(q => q.total_answers === before.stats.find(old => old.id === q.question_id).total + 1));
    assert.equal(latestStats.question_stats.find(q => q.question_type === 'scale').average, 4);
    assert.deepEqual([await responses.evaluate(() => window.__e2eIdentity), await analytics.evaluate(() => window.__e2eIdentity)], before.identities);
    const documents = Object.fromEntries(Object.entries(navigation).map(([name, value]) => [name, value.requests]));
    assert.deepEqual(documents, { responses: 1, analytics: 1 });
    assert.equal(await responses.locator('main select').first().inputValue(), String(survey.id));
    assert.equal(await analytics.locator('main select').first().inputValue(), String(survey.id));
    const chartBars = await analytics.locator('.recharts-bar-rectangle path').count();
    assert.ok(chartBars >= 3);
    assert.deepEqual(errors, []);
    await responses.screenshot({ path: path.join(out, 'responses-after.png'), fullPage: true });
    await analytics.screenshot({ path: path.join(out, 'analytics-after.png'), fullPage: true });
    const answerResponse = await context.request.get(`http://localhost:8000/api/v1/responses/answers?survey_id=${survey.id}`, { headers });
    const answers = await answerResponse.json();
    const initialIds = new Set(initialAnswers.map(answer => answer.id));
    const added = answers.filter(answer => !initialIds.has(answer.id));
    assert.equal(added.length, 4);
    assert.equal(new Set(added.map(answer => answer.session_id)).size, 1);
    const single = survey.questions.find(q => q.type === 'single_choice');
    const multiple = survey.questions.find(q => q.type === 'multiple_choice');
    assert.equal(added.find(answer => answer.question_id === single.id).option_id, single.options.find(option => option.text_uk === 'Через меню бота').id);
    assert.deepEqual([...added.find(answer => answer.question_id === multiple.id).option_ids].sort((a,b) => a-b), multiple.options.filter(option => ['Telegram-бот', 'Адмін-панель'].includes(option.text_uk)).map(option => option.id).sort((a,b) => a-b));
    const result = { verified_at: new Date().toISOString(), method: 'Real Telegram user interaction; two admin pages opened before the session and polled the real API without reload',
      survey_id: survey.id, session_id: added[0].session_id, added_answers: added.length, before,
      after: { rows: answers.length, completed: latestStats.completed_sessions, stats: latestStats.question_stats.map(q => ({ id: q.question_id, type: q.question_type, total: q.total_answers, average: q.average, distribution: q.distribution })) },
      comment, chartBars, polls, documents, frame_events: Object.fromEntries(Object.entries(navigation).map(([name, value]) => [name, value.frameEvents])), same_page_identities: true, filters_preserved: true, errors,
      boundary: 'One controlled survey and one consenting account; not a load test or representative user study' };
    fs.writeFileSync(path.join(out, 'result.json'), JSON.stringify(result, null, 2));
    fs.writeFileSync(path.join(root, process.env.E2E_EVIDENCE_PATH || 'docs/thesis/evidence/telegram-live-closeout-20261118.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify({ survey_id: survey.id, session_id: result.session_id, answers: answers.length, no_reload: true, chartBars }));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
