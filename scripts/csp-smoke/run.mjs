// Headless CSP smoke test against habitreward.org (issue #24 verification).
//
// Verifies:
//   1. /auth/login/ page loads with no CSP / console errors.
//   2. Meta-tag nonce == nonce in style-src-elem header.
//   3. NEGATIVE: injecting an inline <style> block via JS without a valid
//      nonce triggers a securitypolicyviolation (style-src-elem strict).
//   4. POSITIVE: setting an element.style.color via JS does NOT violate
//      (style-src-attr 'unsafe-inline' allows it).
//
// Run: node scripts/csp-smoke/run.mjs [URL]

import { chromium } from 'playwright';

const URL = process.argv[2] || 'https://habitreward.org/auth/login/';

// Negative probe: poll for the synchronously-fired CSP violation, cap so
// a misconfigured (no-violation) policy doesn't hang the test.
const VIOLATION_POLL_TIMEOUT_MS = 2000;
// Positive probe: absence-of-event must be a fixed wait — long enough for
// a violation to have fired if it was going to.
const STYLE_ATTR_ABSENCE_WAIT_MS = 500;

function fail(msg) {
    console.error(`FAIL: ${msg}`);
    process.exitCode = 1;
}

function pass(msg) {
    console.log(`PASS: ${msg}`);
}

const browser = await chromium.launch();
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

const consoleErrors = [];
page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
});
page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`));

// Capture the CSP response header on document navigation.
let cspHeader = null;
page.on('response', (resp) => {
    if (resp.url() === URL || resp.url().replace(/\/$/, '') === URL.replace(/\/$/, '')) {
        cspHeader = resp.headers()['content-security-policy'];
    }
});

const resp = await page.goto(URL, { waitUntil: 'networkidle' });
if (!resp || resp.status() !== 200) {
    fail(`page load status=${resp?.status()}`);
    await browser.close();
    process.exit(1);
}
pass(`page loaded (${resp.status()})`);

// --- Check 1: CSP header parses, has split directives ---
if (!cspHeader) {
    fail('no Content-Security-Policy response header');
} else {
    const directives = {};
    for (const part of cspHeader.split(';')) {
        const trimmed = part.trim();
        if (!trimmed) continue;
        const [name, ...tokens] = trimmed.split(/\s+/);
        directives[name] = tokens;
    }

    if (!directives['style-src-elem']) fail('missing style-src-elem');
    else pass(`style-src-elem present (${directives['style-src-elem'].join(' ')})`);

    if (directives['style-src-elem']?.includes("'unsafe-inline'"))
        fail("style-src-elem still contains 'unsafe-inline'");
    else pass("style-src-elem does NOT contain 'unsafe-inline' (strict)");

    if (!directives['style-src-attr']) fail('missing style-src-attr');
    else pass(`style-src-attr present (${directives['style-src-attr'].join(' ')})`);

    if (!directives['style-src']) fail('missing legacy style-src fallback');
    else pass('legacy style-src fallback present');

    // --- Check 2: meta nonce == header nonce ---
    const headerNonceTok = directives['style-src-elem']?.find((t) => t.startsWith("'nonce-"));
    const headerNonce = headerNonceTok ? headerNonceTok.slice("'nonce-".length, -1) : null;
    const metaNonce = await page.evaluate(() => {
        const m = document.querySelector('meta[name="csp-nonce"]');
        return m ? m.getAttribute('content') : null;
    });

    if (!headerNonce) fail('no nonce token in style-src-elem');
    else if (!metaNonce) fail('no <meta name="csp-nonce"> in document');
    else if (headerNonce === metaNonce) pass(`meta nonce == header nonce (${metaNonce.slice(0, 8)}…)`);
    else fail(`nonce mismatch: header=${headerNonce} meta=${metaNonce}`);
}

// --- Check 3: NEGATIVE — JS-injected <style> without nonce must violate ---
const violations = await page.evaluate((pollLimitMs) => {
    return new Promise((resolve) => {
        const events = [];
        const handler = (e) => events.push({
            blockedURI: e.blockedURI,
            violatedDirective: e.violatedDirective,
            effectiveDirective: e.effectiveDirective,
            sample: e.sample,
        });
        document.addEventListener('securitypolicyviolation', handler);

        // Negative probe: inline <style> block (no nonce, no 'unsafe-inline' on -elem)
        try {
            const s = document.createElement('style');
            s.textContent = 'body { outline: 1px solid red; }';
            document.head.appendChild(s);
        } catch (e) {}

        // Poll for the violation event; short-circuit as soon as it lands.
        // Hard cap (pollLimitMs) keeps the test bounded on a slow browser.
        const start = Date.now();
        const tick = () => {
            if (events.length > 0 || Date.now() - start > pollLimitMs) {
                document.removeEventListener('securitypolicyviolation', handler);
                resolve(events);
            } else {
                setTimeout(tick, 25);
            }
        };
        tick();
    });
}, VIOLATION_POLL_TIMEOUT_MS);

const styleElemViolation = violations.find(
    (v) => v.effectiveDirective?.startsWith('style-src-elem') || v.violatedDirective?.startsWith('style-src-elem'),
);
if (styleElemViolation)
    pass(`<style> injection blocked by ${styleElemViolation.effectiveDirective || styleElemViolation.violatedDirective}`);
else
    fail(`<style> injection NOT blocked — violations seen: ${JSON.stringify(violations)}`);

// --- Check 4: POSITIVE — element.style.X assignment must NOT violate ---
const attrViolations = await page.evaluate((absenceWaitMs) => {
    return new Promise((resolve) => {
        const events = [];
        const handler = (e) => events.push({
            effectiveDirective: e.effectiveDirective,
            violatedDirective: e.violatedDirective,
        });
        document.addEventListener('securitypolicyviolation', handler);

        const d = document.createElement('div');
        d.style.color = 'red';
        d.style.transform = 'translateX(10px)';
        document.body.appendChild(d);

        // Positive probe: absence of an event has no natural completion
        // signal, so we must wait a deterministic window
        // (STYLE_ATTR_ABSENCE_WAIT_MS) for a violation to have fired if it
        // was going to.
        setTimeout(() => {
            document.removeEventListener('securitypolicyviolation', handler);
            d.remove();
            resolve(events);
        }, absenceWaitMs);
    });
}, STYLE_ATTR_ABSENCE_WAIT_MS);

const attrViolation = attrViolations.find(
    (v) => v.effectiveDirective?.startsWith('style-src-attr') || v.violatedDirective?.startsWith('style-src-attr'),
);
if (attrViolation)
    fail(`element.style assignment violated CSP (Vue :style would break!) — ${JSON.stringify(attrViolation)}`);
else
    pass("element.style.* assignment NOT blocked (Vue :style bindings safe)");

// --- Check 5: surface any unexpected console errors ---
if (consoleErrors.length > 0) {
    console.warn(`WARN: ${consoleErrors.length} console error(s) during page load:`);
    for (const e of consoleErrors) console.warn(`  - ${e}`);
} else {
    pass('no console errors during page load');
}

} finally {
    await browser.close();
}
process.exit(process.exitCode ?? 0);
