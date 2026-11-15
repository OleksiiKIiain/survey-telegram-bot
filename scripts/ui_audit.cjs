const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core');
let runningBrowser;

async function main() {
  const output = path.resolve('docs/thesis/evidence');
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  runningBrowser = browser;
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const base = 'http://localhost:5174';
  await page.goto(base + '/login');
  await page.getByRole('button', {name:'Sign in', exact:true}).click();
  await page.getByRole('heading', {name:'Dashboard', exact:true}).waitFor();
  await page.screenshot({path:path.join(output,'dashboard-en.png')});
  await page.getByRole('combobox').selectOption('uk');
  await page.getByRole('heading', {name:'Панель', exact:true}).waitFor();
  await page.screenshot({path:path.join(output,'dashboard-uk.png')});
  for (const [route, name] of [['surveys','Опитування'],['responses','Відповіді'],['analytics','Аналітика'],['respondents','Респонденти']]) {
    await page.goto(base + '/' + route);
    await page.getByRole('heading',{name,exact:true}).waitFor();
    if (route === 'analytics') await page.locator('.recharts-bar-rectangle').first().waitFor();
    else await page.locator('tbody tr').first().waitFor();
    await page.screenshot({path:path.join(output,route+'-uk.png')});
  }
  await page.goto(base + '/surveys/new');
  await page.getByLabel('Назва UA',{exact:true}).fill('Перевірка інтерфейсу');
  await page.getByLabel('Назва EN',{exact:true}).fill('Interface audit');
  await page.getByRole('button',{name:'Додати питання',exact:true}).first().click();
  await page.getByLabel('Питання UA',{exact:true}).fill('Напишіть коментар');
  await page.getByLabel('Питання EN',{exact:true}).fill('Write a comment');
  await page.getByRole('button',{name:'Зберегти опитування',exact:true}).click();
  await page.waitForURL(/\/surveys\/\d+$/);
  const createdUrl = page.url();
  await page.getByRole('link',{name:'Редагувати',exact:true}).click();
  await page.getByLabel('Питання EN',{exact:true}).fill('Saved English translation');
  await page.getByRole('button',{name:'Зберегти опитування',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Зміни успішно збережено.'}).waitFor();
  await page.screenshot({path:path.join(output,'editor-saved.png'),fullPage:true});
  await page.reload();
  await page.getByLabel('Питання EN',{exact:true}).waitFor();
  if (await page.getByLabel('Питання EN',{exact:true}).inputValue() !== 'Saved English translation') throw new Error('Translation did not persist');
  await page.setViewportSize({width:390,height:844});
  await page.goto(base + '/analytics');
  await page.getByRole('heading',{name:'Аналітика',exact:true}).waitFor();
  await page.screenshot({path:path.join(output,'analytics-mobile.png')});
  const overflow = await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth);
  fs.writeFileSync(path.join(output,'ui_audit.json'),JSON.stringify({timestamp:new Date().toISOString(),scope:'Real browser + isolated API/PostgreSQL',login:true,languageSwitch:true,pages:6,translationPersistsAfterReload:true,createdUrl,mobileOverflow:overflow,errors},null,2));
  await browser.close();
  if (errors.length || overflow) throw new Error(JSON.stringify({errors,overflow}));
  console.log('UI audit passed; screenshots and JSON saved');
}
main().catch(async error=>{console.error(error);if(runningBrowser) await runningBrowser.close();process.exitCode=1});
