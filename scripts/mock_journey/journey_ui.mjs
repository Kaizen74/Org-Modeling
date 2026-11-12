// Browser journey: a practitioner's full path through the UI, against the backend
// with the fake Claude (fake_claude_server.py) and the sample org from make_org.py.
// Run by run_checks.sh step 5 on a fresh database.
// Usage: node journey_ui.mjs <frontend-url> <playwright-module> <csv> <compass_handoff.json> [screenshots-dir]
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const [base, pwPath, csvPath, packetPath, shots] = process.argv.slice(2);
const { chromium } = (await import(pwPath)).default;

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
const jsErrors = [], serverErrors = [];
page.on('pageerror', (e) => jsErrors.push(String(e)));
page.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 500) serverErrors.push(`${r.status()} ${r.url()}`); });
page.on('dialog', (d) => d.accept());

const results = [];
const main = () => page.locator('main');
async function waitText(re, ms = 15000) {
  const end = Date.now() + ms;
  let t = '';
  while (Date.now() < end) {
    t = await main().innerText().catch(() => '');
    if (re.test(t)) return t;
    await page.waitForTimeout(250);
  }
  throw new Error(`expected ${re} — page said: ${t.slice(0, 200).replace(/\s+/g, ' ')}`);
}
async function step(name, fn) {
  try { await fn(); results.push([name, true, '']); }
  catch (e) { results.push([name, false, String(e.message || e).slice(0, 300)]); }
}
const go = (p) => page.goto(base + p, { waitUntil: 'networkidle' });
// Screenshots only when a folder is given (for looking at the pages, not for pass/fail)
const shot = (n, p = page) => (shots ? p.screenshot({ path: `${shots}/${n}.png`, fullPage: true }) : null);

await step('settings: save key and test the connection', async () => {
  await go('/settings');
  await page.fill('#apiKey', 'sk-ant-mock-ui-1234');
  await page.getByRole('button', { name: 'Save key' }).click();
  await page.getByRole('button', { name: 'Test the connection' }).click();
  await waitText(/Connection successful/i);
});

await step('upload: Excel CSV through the file picker', async () => {
  await go('/upload');
  await page.setInputFiles('input[type=file]', csvPath);
  await page.getByRole('button', { name: /Upload and analyze/ }).click();
  await waitText(/141/);
  await waitText(/could not be resolved/i);
  await shot('01-upload');
});

await step('compass: broken file refused, good file previewed then imported', async () => {
  const broken = join(mkdtempSync(join(tmpdir(), 'compass-')), 'broken_handoff.json');
  writeFileSync(broken, JSON.stringify({ ...JSON.parse(readFileSync(packetPath, 'utf8')), format: 'something-else' }));
  await go('/upload');
  await page.setInputFiles('[data-testid=compass-file]', broken);
  await waitText(/not a Capability Compass hand-off file[\s\S]*Nothing was changed/i);
  await page.setInputFiles('[data-testid=compass-file]', packetPath);
  await waitText(/nothing is changed until you confirm/i);
  await waitText(/DC-1 Installs the routines in a new unit quickly · 25/);
  if (await page.locator('[data-testid=engagement-key]').count()) throw new Error('engagement key shown before confirming');
  await page.getByRole('button', { name: 'Confirm import' }).click();
  await waitText(/6 comparison criteria set from the file/);
  await page.locator('[data-testid=engagement-key]', { hasText: 'MERIDIAN' }).waitFor();
  await shot('01b-compass-import');
});

await step('overview: health score and departments', async () => {
  await go('/');
  await waitText(/Structural health is \d+ out of 100/);
  await waitText(/6 departments/);
  await shot('02-overview');
});

await step('structure: managers vs benchmark, Level mismatch', async () => {
  await go('/metrics');
  await waitText(/Every manager against the benchmark for their work/);
  await waitText(/Frontline operational/);  // team leads tagged Operational get 10–20
  const lv = await waitText(/Level values? disagrees? with the reporting chain/i);
  if (!/Mei Lin \(Level 3, actually layer 4\)/.test(lv)) throw new Error('Mei Lin mismatch not listed');
  if (/Finance Exec \d \(Level/.test(lv)) throw new Error('people under an unresolved manager listed as Level mismatches');
  await shot('03-structure');
});

await step('org chart: renders and finds a person four layers down', async () => {
  await go('/org-chart');
  await waitText(/managers have a single direct report|managers across/);
  const find = page.getByLabel('Find a person or title');
  await find.fill('Nobody Atall');
  await page.getByRole('button', { name: 'Find', exact: true }).click();
  await waitText(/No one matches/);
  await find.fill('Mei Lin');
  await page.getByRole('button', { name: 'Find', exact: true }).click();
  const t = await waitText(/HR Executive/);
  if (/No one matches/.test(t)) throw new Error('search missed Mei Lin');
  await shot('04-orgchart');
});

await step('work activities: run analysis, see dimension tags', async () => {
  await go('/work-activities');
  await page.getByRole('button', { name: /Run current-state analysis|Re-run analysis/ }).click();
  await waitText(/Stakeholder reporting/);
  await waitText(/Process & Systems/);
  await shot('05-work-activities');
});

await step('AI overlay: optional, opens, AI suggests, user tag applied', async () => {
  await go('/work-activities');
  await page.getByRole('button', { name: /The role of AI in this work/ }).click();
  await page.getByRole('button', { name: /Suggest tags for untagged roles/ }).click();
  await waitText(/roles tagged by the AI/);
  await page.getByLabel(/Show AI capacity in scenarios/).check();
  await waitText(/FTE/);
});

await step('archetypes: run, weighted ranking, grounded diagram', async () => {
  await go('/analysis');
  await waitText(/What the Compass found/i);
  const prefilled = await page.inputValue('textarea[aria-label="Strategy context"]');
  if (!prefilled.startsWith('Who we serve:')) throw new Error(`strategy box not pre-filled: ${prefilled.slice(0, 60)}`);
  await page.fill('#criteria', 'Faster frontline decisions');
  await page.getByRole('button', { name: /Run the analysis|Re-run the analysis/ }).click();
  const t = await waitText(/Front-Back Hybrid/, 30000);
  if (!/Process-Based|weighted/i.test(t)) throw new Error('ranking note not shown');
  if (!/Marketing/.test(t)) throw new Error('invented unit not called out');
  await shot('06-archetypes');
});

await step('hypotheses: H1 added, grade changed, number not reused', async () => {
  const add = async (text) => {
    await page.getByLabel('New hypothesis statement').fill(text);
    await page.getByLabel('New hypothesis refuting evidence').fill('Event records show another role deciding');
    await page.getByRole('button', { name: 'Add hypothesis' }).click();
    await waitText(new RegExp(text));
  };
  await add('Station decides turnaround trade-offs');
  await add('Second hypothesis');
  await page.getByRole('button', { name: 'Delete' }).nth(1).click();
  await add('Third hypothesis');
  const t = await main().innerText();
  if (!/\bH1\b/.test(t) || !/\bH3\b/.test(t) || /\bH2\b/.test(t)) throw new Error('expected H1 and H3 only');
  await page.getByLabel('Grade for H1').selectOption('indicated');
  await waitText(/set by you/);
  await shot('06b-hypotheses');
});

await step('archetypes: build top option as a scenario', async () => {
  await page.getByRole('button', { name: /Build this as a scenario/ }).first().click();
  await page.waitForURL(/scenarios/, { timeout: 10000 });
  await waitText(/Build structural options/);
});

await step('scenarios: quick start removes single-report managers', async () => {
  await go('/scenarios');
  await page.getByRole('button', { name: /Remove the \d+ single-report managers/ }).click();
  await waitText(/5 moves, applied in order/);
  await waitText(/Single-report managers\s+5\s+0/);  // now → scenario in the effect table
});

await step('scenarios: add a role through the form', async () => {
  await page.getByRole('button', { name: 'Add a role', exact: true }).click();
  await page.getByPlaceholder('e.g. Turnaround Coordinator').fill('Turnaround Coordinator');
  const opts = await page.locator('#mv-mgr-list option').evaluateAll((os) => os.map((o) => o.value));
  const vp = opts.find((v) => v.startsWith('Tan Boon Hock'));
  if (!vp) throw new Error('manager not in picker');
  await page.fill('#mv-mgr', vp);
  await page.locator('span.label:has-text("Grade") + input').fill('H5');
  await page.getByRole('button', { name: 'Add move' }).click();
  await waitText(/Turnaround Coordinator/);
  await shot('07-scenario');
});

await step('compare: score a cell, AI fills the rest', async () => {
  await go('/compare');
  await waitText(/Weighted scores/);
  await waitText(/DC-1/);
  await page.getByRole('button', { name: /What the Compass found/ }).click();
  await waitText(/CAP-01\.Structure[\s\S]*Reinforced structure/);
  await page.getByRole('button', { name: 'Score', exact: true }).first().click();
  await page.getByRole('button', { name: /^5\s*strong$/i }).click();
  await page.getByRole('button', { name: 'Save score' }).click();
  await page.getByRole('button', { name: /Suggest judged scores/ }).click();
  await page.getByRole('button', { name: /Suggest judged scores/ }).waitFor({ timeout: 20000 });
  const t = await waitText(/AI · \d\/5/, 20000);
  if (/judged scores are still missing/.test(t)) throw new Error('AI left judged cells unscored');
  if (!/you · 5\/5/.test(t)) throw new Error('your score was not kept');
  await shot('08-compare');
});

await step('implementation: waves and board pack', async () => {
  await go('/implementation');
  await waitText(/people affected/);
  const [pack] = await Promise.all([ctx.waitForEvent('page'), page.getByRole('link', { name: /Open board pack/ }).click()]);
  await pack.waitForLoadState();
  const html = await pack.content();
  if (!/Evidence inventory/.test(html)) throw new Error('pack sections missing');
  const leaked = ['Alicia Seah', 'Tan Boon Hock', 'Jasmine Lim', 'Rachel Ng'].filter((n) => html.includes(n));
  if (leaked.length) throw new Error(`names in pack: ${leaked}`);
  await shot('10-pack', pack);
  await pack.close();
  await shot('09-implementation');
});

await step('return file: link a Compass ID, download matches the screen', async () => {
  await go('/implementation');
  await waitText(/What this app found, in the shared language/i);
  await page.getByLabel('Relate H1 to a Compass ID').selectOption('CAP-04.People');
  await page.locator('[data-finding=H1] button', { hasText: 'CAP-04.People' }).waitFor();
  const ret = await (await page.request.get(base + '/api/v1/compass/return')).json();
  const h1 = ret.findings.find((f) => f.ref === 'H1');
  if (ret.format !== 'compass-return' || ret.engagement_key !== 'MERIDIAN') throw new Error('wrong return header');
  if (h1?.grade !== 'indicated' || h1.relates_to.join() !== 'CAP-04.People') throw new Error(`H1 not as set on screen: ${JSON.stringify(h1)}`);
  const kinds = new Set(ret.findings.map((f) => f.kind));
  for (const k of ['structural_baseline', 'work_activity', 'hypothesis', 'option_score']) if (!kinds.has(k)) throw new Error(`no ${k} finding`);
  const text = await (await page.request.get(base + '/api/v1/compass/return.txt')).text();
  if (!text.includes('[MERIDIAN:H1]')) throw new Error('readable text lacks the engagement-keyed ID');
  for (const n of ['Alicia Seah', 'Tan Boon Hock', 'Jasmine Lim']) if (JSON.stringify(ret).includes(n) || text.includes(n)) throw new Error(`name in return file: ${n}`);
  await shot('09b-findings');
});

await step('layout: no table clipped at laptop width', async () => {
  const clipped = [];
  for (const p of ['/', '/metrics', '/work-activities', '/analysis', '/scenarios', '/compare', '/implementation', '/grades']) {
    await go(p);
    await page.waitForTimeout(1200);
    if (p === '/scenarios') {  // open a scenario so its tables are on the page
      await page.getByRole('button', { name: /Remove single-report managers/ }).first().click();
      await waitText(/Effect on the organization/i);
    }
    const found = await page.$$eval('main .overflow-x-auto', (els) => els
      .filter((e) => e.querySelector('table') && e.scrollWidth > e.clientWidth + 2)
      .map((e) => `${(e.closest('section')?.querySelector('h2,p')?.textContent || '').slice(0, 40)} (${e.scrollWidth}>${e.clientWidth})`));
    found.forEach((f) => clipped.push(`${p}: ${f}`));
  }
  if (clipped.length) throw new Error(clipped.join(' | '));
});

await step('grades: page lists auto-imported grades', async () => {
  await go('/grades');
  await waitText(/H6/);
});

await step('new project: confirm dialog clears everything', async () => {
  await go('/');
  await page.getByRole('button', { name: 'Start a new project' }).click();
  const dlg = await page.getByRole('dialog').innerText();
  if (!/scenario/i.test(dlg)) throw new Error(`dialog does not mention scenarios: ${dlg.replace(/\s+/g, ' ').slice(0, 200)}`);
  await page.getByRole('button', { name: 'Start fresh' }).click();
  await page.waitForTimeout(1500);
  await go('/scenarios');
  await waitText(/No organization to design from/i);
});

if (jsErrors.length) results.push(['no JavaScript errors', false, jsErrors.join(' | ').slice(0, 400)]); else results.push(['no JavaScript errors', true, '']);
if (serverErrors.length) results.push(['no server errors', false, serverErrors.join(' | ')]); else results.push(['no server errors', true, '']);
await browser.close();
for (const [n, ok, d] of results) console.log(`${ok ? 'PASS' : 'FAIL'}  ${n}${ok ? '' : `\n        ${d}`}`);
const passed = results.filter((r) => r[1]).length;
console.log(`\n${passed} of ${results.length} browser checks passed`);
process.exit(passed === results.length ? 0 : 1);
