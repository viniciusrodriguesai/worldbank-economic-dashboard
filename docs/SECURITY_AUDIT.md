# Security audit

Audit date: 2026-08-14  
Baseline revision: `d2fb35f`  
Working branch: `codex/security-production-upgrade`

## Reviewed evidence

The review inspected every tracked application source file, tests, manifests and npm
lockfile, `.gitignore`, `.env.example`, Vite/TypeScript configuration, GitHub Actions,
browser entry points, World Bank and OpenStreetMap flows, CSV creation, and the 101-commit
reachable Git history. README statements were not accepted as implementation evidence.

Baseline before edits:

- `python -m pytest --cov=backend --cov-report=term-missing`: 7 passed; 56% coverage.
- `npm test`: 2 files and 6 tests passed.
- `npm run build`: passed; largest uncompressed chunk was 1,086.49 kB.
- `npm audit` and `npm audit --omit=dev`: 0 vulnerabilities.
- `pip-audit -r backend/requirements.txt`: 11 advisories affecting `requests 2.32.3`
  and transitive `starlette 0.46.2`.
- Ruff: 25 findings. Bandit: one medium-severity B104 finding for the development
  `0.0.0.0`/reload launcher.
- Redacted tracked-file and history pattern scans found no credential. `.env` is ignored,
  has never been tracked, and `.env.example` contains public defaults only.

After dependency commit `25821ae`, pip-audit reported no known vulnerabilities and all
7 backend tests passed on FastAPI 0.141.1, Starlette 1.3.1, and requests 2.34.2.

## Findings

### SEC-001 — Spreadsheet formula injection

- **Severity:** Medium
- **Kind:** Confirmed vulnerability
- **Component / surface:** Frontend CSV export and upstream text fields.
- **Exploitation:** A compromised or unexpected label beginning with `=`, `+`, `-`, or
  `@` remains executable in common spreadsheet software even when CSV-quoted.
- **Evidence:** `ExportCSV.tsx` uses `JSON.stringify` without formula neutralization.
- **Impact:** Opening a downloaded CSV can invoke spreadsheet functions.
- **Remediation:** Use a typed deterministic serializer that prefixes dangerous text,
  quotes CSV correctly, and preserves genuine numeric negatives.
- **Status:** Open; prioritized in the security-remediation commit.
- **Tests:** Formula-prefix, embedded-quote/comma, negative-number, and filename tests.

### SEC-002 — Caller-controlled expensive forecast fitting

- **Severity:** High
- **Kind:** Confirmed resource-exhaustion weakness
- **Component / surface:** Public `/forecast`, CPU, and API workers.
- **Exploitation:** Repeated unauthenticated requests choose arbitrary ARIMA tuples and a
  horizon up to 50 while synchronous fitting has no concurrency control.
- **Evidence:** Public `arima_order`, `years_ahead <= 50`, direct `model.fit()` in request.
- **Impact:** Low-cost denial of service on a portfolio-sized deployment.
- **Remediation:** Remove caller-owned model order, bound candidates/horizon/history,
  enforce fit concurrency and deployment rate/resource limits.
- **Status:** Open; no large product work begins until fixed.
- **Tests:** Parameter bounds, busy capacity, bounded candidates, and failure recovery.

### SEC-003 — Identifier validation does not protect the upstream path

- **Severity:** Medium
- **Kind:** Plausible weakness; not confirmed arbitrary-host SSRF
- **Component / surface:** `country` and `indicator` strings interpolated in World Bank URLs.
- **Exploitation:** Traversal syntax, delimiters, Unicode, or oversized strings probe
  unintended upstream paths. The fixed base prevents direct arbitrary-host selection.
- **Evidence:** Country is length-only; indicator has no maximum/pattern.
- **Impact:** Route confusion, log/error probing, and avoidable resource use.
- **Remediation:** Anchored ASCII formats, length caps, known-metadata validation, HTTPS
  base validation, and cross-host redirect prevention.
- **Status:** Open; prioritized.
- **Tests:** Malformed/unknown country and indicator, encoded delimiters, base URL policy.

### SEC-004 — Upstream errors leak details and use incorrect HTTP semantics

- **Severity:** Medium
- **Kind:** Confirmed weakness
- **Component / surface:** World Bank client, `/data`, `/forecast`, logs and response bodies.
- **Exploitation:** Requests errors include full internal URLs/parameters in a `ValueError`
  that routes may return verbatim as a client `400`.
- **Evidence:** `_fetch_all` constructs detailed errors; routes expose `str(ValueError)`.
- **Impact:** Internal path/configuration disclosure and misleading error handling.
- **Remediation:** Explicit exceptions, sanitized structured logs, safe client messages,
  and 422/502/503/504/500 mapping.
- **Status:** Open; prioritized.
- **Tests:** Timeout, connection, HTTP failure, malformed JSON/envelope, internal failure.

### SEC-005 — Known-vulnerable Python dependencies

- **Severity:** High
- **Kind:** Confirmed dependency risk; exploitability varies by feature
- **Component / surface:** requests and internet-facing Starlette/FastAPI stack.
- **Exploitation:** Published advisories affect installed packages. Some Starlette findings
  involve unused upload/file-response features, but retaining a vulnerable web stack is
  unnecessary; requests processes untrusted upstream I/O.
- **Evidence:** pip-audit baseline: 11 advisories in 2 packages.
- **Impact:** Advisory-dependent confidentiality, integrity, or availability risk.
- **Remediation:** Reviewed compatible pins: requests 2.34.2, FastAPI 0.141.1, Starlette
  1.3.1; pin pip-audit/Bandit/Ruff for repeatable checks.
- **Status:** Fixed in `25821ae`.
- **Tests:** Resolver install, 7 backend tests, pip-audit with 0 known vulnerabilities.

### SEC-006 — Development reloader exposed on all interfaces

- **Severity:** Medium
- **Kind:** Confirmed operational risk
- **Component / surface:** Direct execution of `backend/app.py`.
- **Exploitation:** An operator follows the executable module path and starts reload mode
  bound to `0.0.0.0` outside a controlled local environment.
- **Evidence:** `uvicorn.run(... host=0.0.0.0, reload=True)`; Bandit B104.
- **Impact:** Development-only behavior and a broad listener in production.
- **Remediation:** Remove the launcher; document explicit local and non-reload production
  commands.
- **Status:** Open; prioritized.
- **Tests:** Bandit re-scan and application import/smoke tests.

### SEC-007 — CORS accepts unsafe operator configuration

- **Severity:** Low
- **Kind:** Hardening recommendation
- **Component / surface:** Deployment environment and browser boundary.
- **Exploitation:** An operator configures wildcard or malformed values while believing an
  exact allowlist is enforced.
- **Evidence:** Raw comma splitting is passed to middleware; headers allow `*`.
- **Impact:** API responses become readable from more browser origins than intended.
- **Remediation:** Validate exact HTTP(S) origins; reject wildcard, credentials, paths,
  queries and fragments; keep GET-only, no credentials, and narrow headers.
- **Status:** Open.
- **Tests:** Typed configuration and middleware preflight tests.

### SEC-008 — Cache refresh can amplify an upstream outage

- **Severity:** Low
- **Kind:** Availability hardening recommendation
- **Component / surface:** Metadata cache and `/countries`/`/indicators`.
- **Exploitation:** Once TTL expires, every request after a failed locked refresh retries
  the large metadata load; stale valid metadata is not deliberately served.
- **Evidence:** One timestamp and lock, without stale-on-error or retry backoff.
- **Impact:** Refresh storms and reduced availability during World Bank incidents.
- **Remediation:** Tested cache abstraction with stale-on-error and bounded refresh retry.
- **Status:** Deferred to the architecture phase after immediate security fixes.
- **Tests:** Hit, expiry, refresh failure, concurrent access.

### SEC-009 — GitHub Actions use mutable major tags

- **Severity:** Low
- **Kind:** Supply-chain hardening recommendation
- **Component / surface:** CI action execution.
- **Exploitation:** Compromise or retagging of a mutable action reference changes CI code.
- **Evidence:** `actions/checkout@v4`, `setup-python@v5`, `setup-node@v4`.
- **Impact:** Source/token exposure, reduced by current `contents: read` permissions.
- **Remediation:** Pin reviewed SHAs, retain least privilege, add dependency review and
  automated update configuration.
- **Status:** Deferred to the CI hardening phase.
- **Tests:** Workflow syntax review and published Actions runs.

### SEC-010 — No repository credential detected

- **Severity:** Informational
- **Kind:** Verified control
- **Component / surface:** Tracked source and reachable history.
- **Evidence:** Redacted scans found no private key, GitHub token, or assigned-secret
  pattern. `.env` has no tracked history.
- **Impact:** No credential rotation is indicated by current evidence.
- **Remediation/status:** Keep `.env` ignored, placeholders only, platform secret stores,
  and add automated secret scanning when available.

## Layer ownership

- **FastAPI:** input validation, exception mapping, request/fit bounds, CORS, upstream TLS
  and response validation, safe logs, and health behavior.
- **Frontend host/CDN:** CSP, `frame-ancestors`, HSTS after HTTPS is proven, static caching,
  and source-map publication policy.
- **Reverse proxy/platform:** HTTPS redirect/termination, trusted hosts, request/time limits,
  trusted-client-IP rate limiting, worker/container resource limits, and access logs.

The API should not add decorative browser headers for HTML it does not serve. Deployment
documentation will assign each effective control to the layer that can enforce it.

## Final re-audit

This section will be updated after backend, forecasting, frontend, CI, and deployment
changes. Every item will remain fixed, accepted, or deferred with justification, and no
failed check will be hidden.
