// One-time utility — kept for reference, NOT part of normal CI/CD flow.
//
// Used once to capture the full CSS content nprogress would inject at
// runtime, so we could ship it bundled instead (see
// frontend/src/nprogress.css).  Re-run only if a future Inertia.js
// upgrade changes the nprogress CSS and we need to recapture it.

import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';

const URL = process.argv[2] || 'https://habitreward.org/auth/login/';
const OUT = process.argv[3] || '/tmp/nprogress-injected.css';

const browser = await chromium.launch();
try {
const ctx = await browser.newContext({
    bypassCSP: true,  // let nprogress inject so we can read it
});
const page = await ctx.newPage();

await page.addInitScript(() => {
    window.__capturedCSS = null;
    const origAppend = Element.prototype.appendChild;
    Element.prototype.appendChild = function (node) {
        if (node && node.nodeName === 'STYLE' && node.textContent?.includes('#nprogress')) {
            window.__capturedCSS = node.textContent;
        }
        return origAppend.call(this, node);
    };
});

await page.goto(URL, { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);

const css = await page.evaluate(() => window.__capturedCSS);
if (!css) {
    console.error('No nprogress CSS captured');
    process.exitCode = 1;
} else {
    await writeFile(OUT, css);
    console.log(`Captured ${css.length} chars → ${OUT}`);
    console.log(`\nFirst 300 chars:\n${css.slice(0, 300)}`);
}

} finally {
    await browser.close();
}
process.exit(process.exitCode ?? 0);

