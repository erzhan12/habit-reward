// One-shot: capture the full CSS content nprogress would inject so we
// can ship it bundled instead.

import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';

const URL = process.argv[2] || 'https://habitreward.org/auth/login/';
const OUT = process.argv[3] || '/tmp/nprogress-injected.css';

const browser = await chromium.launch();
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
    process.exit(1);
}

await writeFile(OUT, css);
console.log(`Captured ${css.length} chars → ${OUT}`);
console.log(`\nFirst 300 chars:\n${css.slice(0, 300)}`);

await browser.close();
