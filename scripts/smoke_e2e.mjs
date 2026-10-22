// End-to-end smoke test: real browser → frontend → backend → rendered pages.
// Run by run_checks.sh against servers it starts on spare ports with a throwaway database.
// Usage: node scripts/smoke_e2e.mjs <frontend-url> <playwright-module-path>
const [baseUrl, playwrightPath] = process.argv.slice(2);
const { chromium } = (await import(playwrightPath)).default;

const checks = [
  { path: '/', expect: /Structural health is \d+ out of 100/ },
  { path: '/metrics', expect: /Every manager against the benchmark for their work/ },
  { path: '/org-chart', expect: /managers have a single direct report|managers across/ },
  { path: '/work-activities', expect: /Data coverage|What the work is/ },
  { path: '/analysis', expect: /AI|Analysis/ },
  { path: '/scenarios', expect: /Build structural options and see what each one changes/ },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
page.on('pageerror', (e) => pageErrors.push(String(e)));
let failed = 0;
for (const c of checks) {
  await page.goto(baseUrl + c.path, { waitUntil: 'networkidle' });
  // Pages load data after first paint: wait up to 10s for the expected content
  let text = '';
  let ok = false;
  for (let i = 0; i < 40 && !ok; i++) {
    text = await page.locator('main').innerText();
    ok = c.expect.test(text);
    if (!ok) await page.waitForTimeout(250);
  }
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${c.path}${ok ? '' : ` — page said: ${text.slice(0, 160).replace(/\s+/g, ' ')}`}`);
  if (!ok) failed++;
}
if (pageErrors.length) {
  console.log('FAIL  JavaScript errors:', pageErrors);
  failed++;
}
await browser.close();
process.exit(failed ? 1 : 0);
