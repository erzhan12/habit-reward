# csp-smoke

Playwright-based smoke tests for the production Content-Security-Policy
on habitreward.org. Created during the rollout of [issue #24][issue-24]
(splitting `style-src` into strict `style-src-elem` and permissive
`style-src-attr`).

[issue-24]: https://github.com/erzhan12/habit-reward/issues/24

## Setup

Requires Node.js >= 18 (native ESM, native fetch).

```bash
cd scripts/csp-smoke
npm install        # installs playwright 1.55
npx playwright install chromium   # one-time browser download (~80 MB)
```

## Scripts

### `run.mjs` — main smoke test

Run **after every production deploy** that touches the CSP middleware,
the Vue/Inertia frontend, or the `<base.html>` template.

```bash
node run.mjs                                      # defaults to https://habitreward.org/auth/login/
node run.mjs https://staging.example.com/auth/login/
```

> **Note:** This is a *post-deploy* verification tool that hits a live URL —
> it is intentionally **not** wired into pre-merge CI.  CSP correctness
> depends on the actual served response headers and the bundled assets
> as they ship, neither of which can be exercised at unit-test time
> against a Django test client.  For pre-deploy checks against a
> staging environment, pass the staging URL as the first argument.

Asserts:

1. Page loads with HTTP 200.
2. `style-src-elem` directive is present and contains `'self'`,
   `'nonce-...'`, and `https://fonts.googleapis.com`.
3. `style-src-elem` does NOT contain `'unsafe-inline'` (strict policy).
4. `style-src-attr 'unsafe-inline'` is present (Vue `:style` bindings).
5. Legacy `style-src` fallback is present (pre-CSP3 browsers).
6. `<meta name="csp-nonce">` matches the nonce embedded in the
   `style-src-elem` header — confirms middleware + context processor
   share the same per-request value.
7. **Negative probe** — a JS-injected `<style>` block without a nonce
   triggers a `securitypolicyviolation` (XSS vector closed).
8. **Positive probe** — `element.style.*` assignment does NOT violate
   (Vue `:style="..."` bindings would otherwise break).
9. Surfaces any other console errors on the page (a non-zero count is a
   regression — e.g. a third-party library injecting unnonced styles,
   like the `nprogress` regression that motivated PR #57).

Exit code 0 = all PASS; non-zero = at least one FAIL.

### `diagnose-injections.mjs` — debugging aid

Use when `run.mjs` reports CSP console errors and you need to find what
JavaScript is injecting them. Patches `appendChild` / `insertBefore` to
log every `<style>` insertion with a stack trace.

```bash
node diagnose-injections.mjs                       # defaults to login page
node diagnose-injections.mjs https://...
```

Output identifies the injecting file/function — useful for tracking
down third-party CSP violations like the `@inertiajs/vue3` nprogress
issue.

### `extract-nprogress-css.mjs` — one-time utility

Captured the verbatim nprogress CSS so we could ship it bundled (see
`frontend/src/nprogress.css`). Kept for reference only — rerun if an
Inertia.js upgrade changes the nprogress CSS and we need to recapture.

## Failure interpretation

| Symptom | Likely cause |
| --- | --- |
| `FAIL: style-src-elem still contains 'unsafe-inline'` | Middleware regression — someone reverted PR #56. |
| `FAIL: nonce mismatch` | Context processor and middleware emitted different nonces — likely a middleware ordering or caching change. |
| `FAIL: <style> injection NOT blocked` | The strict policy weakened — the XSS vector is open again. **Treat as P0**. |
| `FAIL: element.style.* assignment violated CSP` | `style-src-attr 'unsafe-inline'` removed or restricted — every Vue `:style` binding in the app would break. |
| `WARN: N console error(s)` listing `Refused to apply inline style` | Some new JS is injecting unnonced `<style>` blocks. Run `diagnose-injections.mjs` to find the source. |
