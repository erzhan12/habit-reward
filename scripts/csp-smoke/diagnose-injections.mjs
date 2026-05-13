// Diagnose: capture the textContent of every <style> tag in the DOM after
// page load to identify what's injecting unnonced inline styles.

import { chromium } from 'playwright';

const URL = process.argv[2] || 'https://habitreward.org/auth/login/';

const browser = await chromium.launch();
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

// Patch document.head.appendChild to log <style> insertions with their content.
await page.addInitScript(() => {
    window.__injectedStyles = [];
    const origAppend = Element.prototype.appendChild;
    Element.prototype.appendChild = function (node) {
        if (node && node.nodeName === 'STYLE') {
            window.__injectedStyles.push({
                target: this.nodeName,
                hasNonce: !!node.nonce || !!node.getAttribute('nonce'),
                preview: (node.textContent || '').slice(0, 200),
                length: (node.textContent || '').length,
                stack: new Error().stack,
            });
        }
        return origAppend.call(this, node);
    };
    const origInsert = Element.prototype.insertBefore;
    Element.prototype.insertBefore = function (node, ref) {
        if (node && node.nodeName === 'STYLE') {
            window.__injectedStyles.push({
                target: this.nodeName,
                via: 'insertBefore',
                hasNonce: !!node.nonce || !!node.getAttribute('nonce'),
                preview: (node.textContent || '').slice(0, 200),
                length: (node.textContent || '').length,
                stack: new Error().stack,
            });
        }
        return origInsert.call(this, node, ref);
    };
});

await page.goto(URL, { waitUntil: 'networkidle' });

// Allow Vue hydration to fully settle.
await page.waitForTimeout(1500);

const injected = await page.evaluate(() => window.__injectedStyles || []);

console.log(`Found ${injected.length} dynamic <style> insertion attempt(s):\n`);
for (const [i, info] of injected.entries()) {
    console.log(`[${i + 1}] target=${info.target} hasNonce=${info.hasNonce} length=${info.length}`);
    console.log(`    preview: ${info.preview.replace(/\s+/g, ' ').slice(0, 160)}`);
    const stackLines = info.stack.split('\n').slice(1, 5);
    console.log(`    stack:   ${stackLines[0]?.trim()}`);
    console.log(`             ${stackLines[1]?.trim()}`);
    console.log('');
}

// Also list <style> tags currently in DOM (in case some were created via innerHTML).
const dom = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('style')).map((s) => ({
        nonce: s.nonce || s.getAttribute('nonce') || null,
        preview: (s.textContent || '').slice(0, 200).replace(/\s+/g, ' '),
        length: (s.textContent || '').length,
    }));
});
console.log(`\nDOM has ${dom.length} <style> tag(s) at the end:`);
for (const [i, s] of dom.entries()) {
    console.log(`[${i + 1}] nonce=${s.nonce} length=${s.length}`);
    console.log(`    preview: ${s.preview.slice(0, 160)}`);
}

} finally {
    await browser.close();
}
