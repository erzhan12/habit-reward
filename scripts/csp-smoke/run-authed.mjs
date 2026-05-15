// Authenticated CSP smoke test.  Launches a visible Chromium browser,
// fills the Telegram username on the login page, then *waits* up to 3
// minutes for you to tap "Confirm" in Telegram.  Once the dashboard
// loads, walks the protected pages and reports any CSP / console
// errors per page.
//
// Run: node run-authed.mjs <telegram-username>
// Example: node run-authed.mjs erzhan

import { chromium } from 'playwright';

const USERNAME = process.argv[2];
const ORIGIN = process.argv[3] || 'https://habitreward.org';
const LOGIN_TIMEOUT_MS = 180_000;

if (!USERNAME) {
    console.error('Usage: node run-authed.mjs <telegram-username> [origin]');
    process.exit(1);
}

const browser = await chromium.launch({ headless: false });
try {
const ctx = await browser.newContext();
const page = await ctx.newPage();

// --- Step 1: navigate to login, submit username ---
console.log(`Opening ${ORIGIN}/auth/login/ — confirm via Telegram when prompted.`);
await page.goto(`${ORIGIN}/auth/login/`, { waitUntil: 'networkidle' });
await page.locator('input[name=""], input[autocomplete=username], input[type=text]').first().fill(USERNAME);
await page.locator('button[type=submit]').first().click();

// --- Step 2: wait for redirect off /auth/login/ ---
console.log('Waiting for you to tap "Confirm" in Telegram (up to 3 minutes)...');
let loggedIn = false;
try {
    await page.waitForURL((url) => !url.pathname.startsWith('/auth/'), { timeout: LOGIN_TIMEOUT_MS });
    loggedIn = true;
} catch (e) {
    console.error('FAIL: timed out waiting for Telegram confirmation.');
    process.exitCode = 1;
}

if (loggedIn) {
console.log(`Logged in: ${page.url()}`);

// --- Step 3: walk protected pages, collect console errors per page ---
const PAGES = ['/', '/rewards/', '/streaks/', '/history/', '/analytics/'];

for (const path of PAGES) {
    const errors = [];
    const onError = (msg) => { if (msg.type() === 'error') errors.push(msg.text()); };
    page.on('console', onError);
    page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));

    try {
        const resp = await page.goto(`${ORIGIN}${path}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(1500);  // let entrance animations and :style bindings settle

        const cspErrors = errors.filter((e) => /content security policy|refused to apply inline style/i.test(e));
        const otherErrors = errors.filter((e) => !cspErrors.includes(e));

        if (resp?.status() !== 200) {
            console.log(`FAIL ${path}: HTTP ${resp?.status()}`);
            process.exitCode = 1;
        } else if (cspErrors.length === 0 && otherErrors.length === 0) {
            console.log(`PASS ${path}: HTTP 200, no console errors`);
        } else {
            if (cspErrors.length > 0) {
                console.log(`FAIL ${path}: ${cspErrors.length} CSP violation(s):`);
                for (const e of cspErrors) console.log(`  - ${e.slice(0, 200)}`);
                process.exitCode = 1;
            }
            if (otherErrors.length > 0) {
                console.log(`WARN ${path}: ${otherErrors.length} non-CSP console error(s):`);
                for (const e of otherErrors) console.log(`  - ${e.slice(0, 200)}`);
            }
        }
    } finally {
        page.off('console', onError);
    }
}
}  // end if (loggedIn)

} finally {
    await browser.close();
}
process.exit(process.exitCode ?? 0);
