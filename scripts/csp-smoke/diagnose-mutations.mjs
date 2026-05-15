// Diagnose: use MutationObserver to catch any <style> tag added to the
// DOM, regardless of which API was used (appendChild, insertBefore,
// innerHTML, insertAdjacentHTML, Range.insertNode, etc.).

import { chromium } from 'playwright';

const TARGET = process.argv[2] || 'https://habitreward.org/auth/login/';

const browser = await chromium.launch();
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

await page.addInitScript(() => {
    window.__styleNodes = [];
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeName === 'STYLE') {
                    window.__styleNodes.push({
                        target: m.target.nodeName,
                        hasNonce: !!node.nonce || !!node.getAttribute('nonce'),
                        preview: (node.textContent || '').slice(0, 200).replace(/\s+/g, ' '),
                        length: (node.textContent || '').length,
                    });
                }
                if (node.nodeName === 'LINK' && node.rel === 'stylesheet') {
                    window.__styleNodes.push({
                        target: m.target.nodeName,
                        link: true,
                        href: node.href,
                    });
                }
            }
        }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
});

await page.goto(TARGET, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

const nodes = await page.evaluate(() => window.__styleNodes || []);

console.log(`Captured ${nodes.length} <style>/<link rel=stylesheet> insertion(s):\n`);
for (const [i, info] of nodes.entries()) {
    if (info.link) {
        console.log(`[${i + 1}] <link rel=stylesheet> href=${info.href} target=${info.target}`);
    } else {
        console.log(`[${i + 1}] <style> target=${info.target} hasNonce=${info.hasNonce} length=${info.length}`);
        console.log(`    preview: ${info.preview}`);
    }
}

// Also list adoptedStyleSheets which bypass <style>/<link> entirely.
const adopted = await page.evaluate(() => {
    return document.adoptedStyleSheets?.map((s) => {
        const rules = [];
        for (const rule of s.cssRules || []) rules.push(rule.cssText.slice(0, 100));
        return { ruleCount: s.cssRules?.length, sample: rules.slice(0, 3) };
    }) || [];
});
console.log(`\ndocument.adoptedStyleSheets: ${adopted.length} stylesheet(s)`);
for (const [i, a] of adopted.entries()) {
    console.log(`[${i + 1}] ${a.ruleCount} rules; sample: ${JSON.stringify(a.sample)}`);
}

} finally {
    await browser.close();
}
