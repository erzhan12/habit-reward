// Print full details of every securitypolicyviolation event on the page.

import { chromium } from 'playwright';

const TARGET = process.argv[2] || 'https://habitreward.org/auth/login/';

const browser = await chromium.launch();
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

await page.addInitScript(() => {
    window.__violations = [];
    document.addEventListener('securitypolicyviolation', (e) => {
        window.__violations.push({
            blockedURI: e.blockedURI,
            violatedDirective: e.violatedDirective,
            effectiveDirective: e.effectiveDirective,
            sourceFile: e.sourceFile,
            lineNumber: e.lineNumber,
            columnNumber: e.columnNumber,
            sample: e.sample,
            documentURI: e.documentURI,
        });
    });
});

await page.goto(TARGET, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

const violations = await page.evaluate(() => window.__violations || []);
console.log(`Captured ${violations.length} violation(s):\n`);
for (const [i, v] of violations.entries()) {
    console.log(`[${i + 1}] effectiveDirective: ${v.effectiveDirective}`);
    console.log(`    blockedURI:   ${v.blockedURI || '(inline)'}`);
    console.log(`    sourceFile:   ${v.sourceFile || '(none)'}`);
    console.log(`    line:column:  ${v.lineNumber}:${v.columnNumber}`);
    console.log(`    sample:       ${v.sample?.slice(0, 200) || '(empty)'}`);
    console.log('');
}

} finally {
    await browser.close();
}
