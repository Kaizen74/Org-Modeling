// Browser journey: a practitioner's full path through the UI, against the backend
// with the fake Claude (fake_claude_server.py) and the sample org from make_org.py.
// Run by run_checks.sh step 5 on a fresh database.
// Usage: node journey_ui.mjs <frontend-url> <playwright-module> <csv> <compass_handoff.json> <countries_fixture_dir> [screenshots-dir]
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const [base, pwPath, csvPath, packetPath, countriesDir, shots] = process.argv.slice(2);
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
  await waitText(/suggested from Work Type Operational/);  // Operational team leads start as suggested Supervisors (10–20)
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

// ---------------- Roles and structure by country (the countries PRD acceptance flow)

await step('countries: upload, by-country view and filters', async () => {
  await go('/upload');
  await page.setInputFiles('input[type=file][accept=".csv"]', join(countriesDir, 'meridian_org_by_country.csv'));
  await page.getByRole('button', { name: /Upload and analyze/ }).click();
  await waitText(/84/);
  await go('/metrics');
  const t = await waitText(/The same lenses, country by country/i);
  if (!/⚑ one layer more than Arden/.test(t)) throw new Error('Caldera layer difference not stated');
  if (!/Salaries are read as one currency/.test(t)) throw new Error('currency note missing');
  await page.getByLabel('Filter by country').first().selectOption('Belmar');
  await waitText(/Departments in Belmar/);
  await go('/org-chart');
  await page.getByLabel('Filter by country').selectOption('Caldera');
  await waitText(/Showing the 28 people who work in Caldera/);
  await shot('11-countries');
});

await step('countries: three packets link by country; Belmar again says replace', async () => {
  for (const c of ['arden', 'belmar', 'caldera']) {
    await go('/upload');
    await page.setInputFiles('[data-testid=compass-file]', join(countriesDir, `${c}_compass_handoff.json`));
    const t = await waitText(/nothing is changed until you confirm/i);
    const name = c[0].toUpperCase() + c.slice(1);
    if (!new RegExp(`Links to ${name}\\.`).test(t)) throw new Error(`${name} not matched by name: ${(await page.getByTestId('link-target').innerText())}`);
    await page.getByRole('button', { name: 'Confirm import' }).click();
    await waitText(new RegExp(`Linked ${name} to engagement`));
  }
  await page.setInputFiles('[data-testid=compass-file]', join(countriesDir, 'belmar_compass_handoff.json'));
  await waitText(/will be replaced/);
  await page.getByRole('button', { name: 'Cancel' }).click();
  await page.locator('[data-testid=engagement-key]', { hasText: 'MERIDIAN · 3 countries' }).waitFor();
});

await step('countries: Compass roles screen matches the acceptance table', async () => {
  await go('/compass-roles');
  await page.getByRole('button', { name: /Accept 16 exact title matches/ }).click();
  for (const ref of ['RL-010', 'RL-012', 'RL-017']) {
    await page.locator(`[data-role="${ref}"]`).getByRole('button', { name: /Match…/ }).click();
    await page.getByRole('button', { name: 'No job title in this file' }).click();
    await page.locator(`[data-role="${ref}"]`, { hasText: 'No job title in this file' }).waitFor();
  }
  const cellText = async (ref, i) => (await page.locator(`[data-role="${ref}"] td`).nth(i + 1).innerText()).replace(/\s+/g, ' ');
  const want = { 'RL-011': ['0 holders · Compass: Absent', '1 holder · Compass: Exists', '0 holders · Compass: Absent'],
                 'RL-004': ['1 holder · Compass: Thin', '0 holders · Compass: Absent', '2 holders · Compass: Exists'],
                 'RL-018': ['0 holders · Compass: Absent', '0 holders · Compass: Absent', '1 holder · To confirm'] };
  for (const [ref, cells] of Object.entries(want)) {
    for (let i = 0; i < 3; i++) {
      const got = await cellText(ref, i);
      if (!got.startsWith(cells[i])) throw new Error(`${ref} column ${i + 1}: "${got.slice(0, 80)}"`);
    }
  }
  if (!(await cellText('RL-018', 2)).includes('Still to confirm in the Compass; the org file shows 1 person.')) throw new Error('RL-018 Caldera not flagged');
  if (!(await cellText('RL-004', 1)).includes('Why is it missing? Not recorded.')) throw new Error('empty role is silent');
  await shot('12-compass-roles');
});

await step('countries: record Belmar RL-011 reason, export Belmar file', async () => {
  await page.locator('[data-role="RL-011"] td').nth(2).getByRole('button', { name: 'Record reason' }).click();
  const editor = page.getByRole('region', { name: /Reason for RL-011 in Belmar/ });
  await editor.getByRole('radio', { name: 'Chosen' }).click();
  await editor.getByLabel('In one line').fill('Created in 2023 when Belmar won its two largest renewal contracts; Arden leaves pricing to finance.');
  await editor.getByLabel('Compared with (optional)').selectOption('Arden');
  await editor.getByRole('button', { name: 'Save reason' }).click();
  await page.locator('[data-role="RL-011"]', { hasText: 'Chosen vs Arden' }).waitFor();

  await go('/implementation');
  await page.getByRole('group', { name: 'Which file to export' }).getByRole('button', { name: /Belmar · MERIDIANBE/ }).click();
  await waitText(/Why Head of Pricing \/ Revenue Management exists in Belmar/);
  const href = await page.getByRole('link', { name: /Download Belmar's file/ }).getAttribute('href');
  const ret = await (await page.request.get(base + href)).json();
  const byRef = Object.fromEntries(ret.findings.map((f) => [f.ref, f]));
  if (ret.country !== 'Belmar' || ret.engagement_key !== 'MERIDIANBE') throw new Error('wrong header');
  if (byRef['baseline.layers']?.figure !== '5 layers') throw new Error('Belmar layers wrong');
  if (byRef['RL-011']?.reason_class !== 'chosen' || byRef['RL-011']?.compared_with !== 'Arden') throw new Error('RL-011 reason not exported as set on screen');
  const empty = ['RL-004', 'RL-007', 'RL-008', 'RL-010', 'RL-012', 'RL-017', 'RL-018'];
  if (!empty.every((r) => byRef[r]?.reason_class === 'unknown' && byRef[r]?.figure === '0 people')) throw new Error('empty Belmar roles missing');
  if (/\b[A-Z]{2} Person \d{3}\b|\bE\d{3}\b/.test(JSON.stringify(ret))) throw new Error('name or Employee ID in the file');
  await shot('13-belmar-export');
});

// ---------------- Structure numbers for the Compass: manager types, settings, role families, broken lines

await step('structure: unit view shows types, base salary; a type set on screen recounts Belmar', async () => {
  await go('/metrics');
  const t = await waitText(/Median span by manager type/);
  if (!/Managers without a confirmed type/.test(t) || !/Base salary only\. Overtime, benefits and employer contributions are not included\./.test(t)) throw new Error('type rows or base-salary note missing');
  await page.getByLabel('Filter by country').first().selectOption('Belmar');
  await page.getByLabel('Manager type for BE Person 034').selectOption('specialist_lead');
  const row = page.locator('tr', { hasText: 'Managers within their span benchmark' });
  await row.filter({ hasText: '2 of 9' }).waitFor({ timeout: 10000 });
  await page.getByLabel('Manager type for BE Person 034').selectOption('');
  await row.filter({ hasText: '1 of 9' }).waitFor({ timeout: 10000 });
});

await step('settings: span ranges and supervisory words saved, then reset', async () => {
  await go('/settings');
  await waitText(/Span ranges by manager type/);
  await page.getByLabel('Supervisor from').fill('2');
  await page.getByRole('button', { name: 'Save structure settings' }).click();
  await waitText(/Saved\. Spans are recalculated/);
  await page.getByLabel('Supervisor from').fill('30');
  await page.getByRole('button', { name: 'Save structure settings' }).click();
  await waitText(/Supervisor: the range must run/);
  await page.getByRole('button', { name: 'Reset to starting points' }).click();
  await waitText(/Back to the starting ranges and words/);
  if ((await page.getByLabel('Supervisor from').inputValue()) !== '10') throw new Error('reset did not restore 10');
});

await step('role families: confirm six from suggestions, why RF-03 is only in Belmar', async () => {
  await go('/role-families');
  await waitText(/Suggested from shared key words/i);
  const plan = [['Load control', 'Load control'], ['Ramp', 'Ramp handling'], ['Pricing', 'Pricing and revenue management'],
                ['Analytics & AI', 'Analytics and AI'], ['Hub duty', 'Disruption control'], ['Finance', 'Finance']];
  for (const [suggested, name] of plan) {
    const row = page.locator(`[data-suggestion="${suggested}"]`);
    await row.getByLabel(`Family name for ${suggested}`).fill(name);
    await row.getByRole('button', { name: 'Confirm family' }).click();
    await page.locator('[data-family]', { has: page.locator(`input[value="${name}"]`) }).waitFor();
  }
  await page.getByLabel('Add a job title to RF-02').selectOption('Shift Supervisor');
  await page.locator('[data-family="RF-02"]', { hasText: 'Shift Supervisor' }).waitFor();
  const across = (ref) => page.locator(`[data-across="${ref}"]`);
  await across('RF-03').filter({ hasText: 'Only in Belmar' }).waitFor();
  for (const ref of ['RF-04', 'RF-05']) await across(ref).filter({ hasText: 'In some' }).waitFor();
  for (const ref of ['RF-01', 'RF-02', 'RF-06']) await across(ref).filter({ hasText: 'In every country' }).waitFor();
  await across('RF-03').locator('td').nth(2).getByRole('button', { name: 'Why?' }).click();
  const editor = page.getByRole('region', { name: 'Why RF-03 in Belmar' });
  await editor.getByRole('radio', { name: 'Chosen' }).click();
  await editor.getByLabel('In one sentence').fill('Created in 2023 when Belmar won its two largest renewal contracts.');
  await editor.getByLabel('Compared with (optional)').selectOption('Arden');
  await editor.getByRole('button', { name: 'Save reason' }).click();
  await across('RF-03').filter({ hasText: 'Chosen vs Arden' }).waitFor();
  await shot('14-role-families');
});

await step('role families: Belmar export matches the Compass sample field for field', async () => {
  await go('/implementation');
  await page.getByRole('group', { name: 'Which file to export' }).getByRole('button', { name: /Belmar · MERIDIANBE/ }).click();
  await waitText(/Pricing and revenue management/);
  const href = await page.getByRole('link', { name: /Download Belmar's file/ }).getAttribute('href');
  const ret = await (await page.request.get(base + href)).json();
  const sample = JSON.parse(readFileSync(join(countriesDir, 'belmar_return_org_modeling.json'), 'utf8'));
  const pick = (r) => Object.fromEntries(r.findings.filter((f) => f.kind === 'role_family').map((f) => [f.ref, f]));
  const ours = pick(ret), theirs = pick(sample);
  const canon = (o) => JSON.stringify(o, Object.keys(o).sort());
  for (const ref of Object.keys(theirs)) {
    if (!ours[ref]) throw new Error(`${ref} missing`);
    for (const k of Object.keys(theirs[ref])) if (JSON.stringify(ours[ref][k]) !== JSON.stringify(theirs[ref][k])) throw new Error(`${ref}.${k}: ${JSON.stringify(ours[ref][k])} vs ${JSON.stringify(theirs[ref][k])}`);
    if (Object.keys(ours[ref]).length !== Object.keys(theirs[ref]).length) throw new Error(`${ref} has extra fields: ${canon(ours[ref])}`);
  }
  const m = ret.findings.find((f) => f.ref === 'baseline.layers').metrics;
  if (m.total_cost !== 2263000 || m.median_span !== 2 || m.spans_within !== 1) throw new Error(`metrics wrong: ${JSON.stringify(m)}`);
  if (/\b[A-Z]{2} Person \d{3}\b|\bE\d{3}\b/.test(JSON.stringify(ret))) throw new Error('name or Employee ID in the file');
});

await step('broken lines: blanked Ramp Agents hide Belmar spans and name the people', async () => {
  const rows = readFileSync(join(countriesDir, 'meridian_org_by_country.csv'), 'utf8').trim().split('\n');
  const head = rows[0].split(',');
  const col = (n) => head.indexOf(n);
  const fixed = rows.map((line, i) => {
    if (!i) return line;
    const cells = line.split(',');
    if (cells[col('Country')] === 'Belmar' && cells[col('Job Title')] === 'Ramp Agent') { cells[col('Line Manager')] = ''; cells[col('Line Manager ID')] = ''; }
    return cells.join(',');
  });
  const broken = join(mkdtempSync(join(tmpdir(), 'broken-')), 'broken.csv');
  writeFileSync(broken, fixed.join('\n') + '\n');
  await go('/upload');
  await page.setInputFiles('input[type=file][accept=".csv"]', broken);
  await page.getByRole('button', { name: /Upload and analyze/ }).click();
  await waitText(/84/);
  await go('/metrics');
  const t = await waitText(/Reporting lines look incomplete in Belmar/);
  if (!/hidden: reporting lines incomplete/.test(t)) throw new Error('Belmar spans not hidden');
  if (!/BE Person 05\d · Ramp Agent — no line manager/.test(t)) throw new Error('people concerned not listed');
  await shot('15-broken-lines');
});

if (jsErrors.length) results.push(['no JavaScript errors', false, jsErrors.join(' | ').slice(0, 400)]); else results.push(['no JavaScript errors', true, '']);
if (serverErrors.length) results.push(['no server errors', false, serverErrors.join(' | ')]); else results.push(['no server errors', true, '']);
await browser.close();
for (const [n, ok, d] of results) console.log(`${ok ? 'PASS' : 'FAIL'}  ${n}${ok ? '' : `\n        ${d}`}`);
const passed = results.filter((r) => r[1]).length;
console.log(`\n${passed} of ${results.length} browser checks passed`);
process.exit(passed === results.length ? 0 : 1);
