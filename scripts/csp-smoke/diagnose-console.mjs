// Capture every console message + the raw violation event with the full
// stack trace from the page's perspective.

import { chromium } from 'playwright';

const TARGET = process.argv[2] || 'https://habitreward.org/auth/login/';

const browser = await chromium.launch();
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

// Patch every plausible style-injection path BEFORE any script runs.
await page.addInitScript(() => {
    window.__injections = [];

    const record = (where, node, extra = {}) => {
        if (!node || node.nodeName !== 'STYLE') return;
        window.__injections.push({
            where,
            hasNonce: !!node.nonce || !!node.getAttribute('nonce'),
            preview: (node.textContent || '').slice(0, 200).replace(/\s+/g, ' '),
            length: (node.textContent || '').length,
            stack: new Error().stack.split('\n').slice(2, 8).map((l) => l.trim()),
            ...extra,
        });
    };

    // Patch Node.prototype methods (Element.prototype inherits from Node).
    for (const method of ['appendChild', 'insertBefore', 'replaceChild']) {
        const orig = Node.prototype[method];
        Node.prototype[method] = function (...args) {
            record(`Node.${method}`, args[0]);
            return orig.apply(this, args);
        };
    }
    for (const method of ['append', 'prepend', 'before', 'after', 'replaceWith']) {
        const orig = Element.prototype[method];
        Element.prototype[method] = function (...args) {
            for (const a of args) record(`Element.${method}`, a);
            return orig.apply(this, args);
        };
    }
    // innerHTML / outerHTML setters can inject <style> via parsing.
    const innerHTMLDesc = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
    Object.defineProperty(Element.prototype, 'innerHTML', {
        ...innerHTMLDesc,
        set(value) {
            if (typeof value === 'string' && /<style[\s>]/i.test(value)) {
                window.__injections.push({
                    where: 'innerHTML=',
                    target: this.nodeName,
                    preview: value.slice(0, 200),
                    stack: new Error().stack.split('\n').slice(2, 8).map((l) => l.trim()),
                });
            }
            return innerHTMLDesc.set.call(this, value);
        },
    });

    // Also catch violations.
    document.addEventListener('securitypolicyviolation', (e) => {
        window.__injections.push({
            where: 'CSP-violation-event',
            sourceFile: e.sourceFile,
            lineNumber: e.lineNumber,
            sample: e.sample,
        });
    });
});

page.on('console', (msg) => {
    if (msg.type() === 'error') {
        console.log(`[console.error] ${msg.text().slice(0, 300)}`);
        for (const arg of msg.location ? [msg.location()] : []) {
            console.log(`  at ${arg.url}:${arg.lineNumber}:${arg.columnNumber}`);
        }
    }
});

await page.goto(TARGET, { waitUntil: 'networkidle' });
await page.waitForTimeout(2000);

const injections = await page.evaluate(() => window.__injections || []);
console.log(`\nIn-page captured ${injections.length} event(s):`);
for (const [i, info] of injections.entries()) {
    console.log(`[${i + 1}] where=${info.where} ${info.hasNonce !== undefined ? `hasNonce=${info.hasNonce}` : ''} length=${info.length || '?'}`);
    if (info.preview) console.log(`    preview: ${info.preview}`);
    if (info.stack) for (const s of info.stack) console.log(`    stack:   ${s}`);
    if (info.sourceFile) console.log(`    sourceFile: ${info.sourceFile}:${info.lineNumber}`);
    if (info.sample) console.log(`    sample:  ${info.sample.slice(0, 200)}`);
}

} finally {
    await browser.close();
}
