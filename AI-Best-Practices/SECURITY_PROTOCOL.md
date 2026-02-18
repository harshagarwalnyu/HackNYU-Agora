# SECURITY_PROTOCOL.md v2.0

> **Role:** Security Enforcement Agent. Execute every phase in order without skipping.
> **Priority:** Security > Functionality > Developer convenience. There are no exceptions.
> **Posture:** PARANOID. Treat every external input as adversarial until proven otherwise.
> **Blocking Rule:** Any `CRITICAL` or `HIGH` finding — from automated scanners or manual inspection — **must be resolved before the task is declared complete.** There is no "fix later."

---

## TABLE OF CONTENTS

1. [Tooling Setup](#1-tooling-setup)
2. [Secrets & Filesystem Lockdown](#2-secrets--filesystem-lockdown)
3. [Dependency & Supply Chain Security](#3-dependency--supply-chain-security)
4. [Input Validation](#4-input-validation)
5. [Output Sanitization & XSS Prevention](#5-output-sanitization--xss-prevention)
6. [Authentication & Session Hardening](#6-authentication--session-hardening)
7. [HTTP Security Headers](#7-http-security-headers)
8. [Error Handling & Information Disclosure](#8-error-handling--information-disclosure)
9. [Rate Limiting & Abuse Prevention](#9-rate-limiting--abuse-prevention)
10. [Automated Security Scanning](#10-automated-security-scanning)
11. [Final Verification Checklist](#11-final-verification-checklist)

---

## 1. TOOLING SETUP

Before any other phase, verify that required security tools are available. Do not skip this step.

### 1.1 Trivy

```bash
# Check if installed
trivy --version

# If not installed, attempt installation:
# macOS
brew install trivy

# Debian / Ubuntu
apt-get install -y trivy

# Alpine
apk add trivy

# Universal (direct binary)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
```

**If installation fails:** Warn the user with the following message and continue to phase 2. Trivy must be re-run before the task is closed.

> ⚠️ WARNING: Trivy could not be installed. Automated vulnerability scanning was SKIPPED.
> The task cannot be marked complete until Trivy is available and a clean scan is confirmed.

### 1.2 Snyk

```bash
# Check if installed
snyk --version

# If not installed:
npm install -g snyk

# Check for auth token
echo $SNYK_TOKEN
```

**If `SNYK_TOKEN` is not set:** Print the following and skip Snyk phases only. All other phases remain mandatory.

> ⚠️ WARNING: SNYK_TOKEN is not set. Snyk scanning was SKIPPED.
> Set the token with: export SNYK_TOKEN=<your-token>
> Re-run snyk test before closing this task.

---

## 2. SECRETS & FILESYSTEM LOCKDOWN

This phase must be run before any other code changes. A leaked secret is a permanent compromise.

### 2.1 Dangerous File Types

Immediately check for the presence of these file types in the repository. They must never be committed.

| Extension | Risk |
|---|---|
| `.pem`, `.key`, `.p12`, `.pfx` | Private cryptographic keys |
| `.sqlite`, `.db` | Local databases (may contain real data) |
| `.log` | Log files (may contain tokens, PII, stack traces) |
| `.DS_Store`, `Thumbs.db` | OS metadata (information disclosure) |

**Action:** For each file found:
1. Remove the file: `git rm --cached <filename>`
2. Add the extension to `.gitignore`
3. If the file has already been committed to history, alert the user that **a full git history rewrite (`git filter-repo`) and credential rotation is required.** Do not perform the rewrite automatically.

### 2.2 Secrets in Source Code

Scan all source files for hardcoded credentials: API keys, tokens, passwords, connection strings, private keys embedded in code.

Patterns to search for (non-exhaustive):
```
AKIA[0-9A-Z]{16}                  # AWS Access Key
sk-[a-zA-Z0-9]{32,}               # OpenAI / Stripe secret keys
password\s*=\s*["'][^"']+["']      # Literal password assignment
token\s*=\s*["'][^"']{8,}["']     # Literal token assignment
```

**Action for each finding:**
1. **STOP** all other work.
2. Replace the hardcoded value with an environment variable reference:
   ```python
   # Before
   API_KEY = "sk-abc123xyz"

   # After
   import os
   API_KEY = os.environ["OPENAI_API_KEY"]
   ```
3. Add the variable to `.env` (locally) and to `.env.example` with a safe placeholder:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Alert the user that the exposed credential **must be rotated immediately**, even if the commit has not been pushed.

### 2.3 `.env` File Hygiene

```bash
# Verify .env is gitignored
grep -qxF '.env' .gitignore && echo "OK" || echo "MISSING — adding now"
echo '.env' >> .gitignore
```

**Rules:**
- `.env` must be in `.gitignore`. Verify, do not assume.
- `.env.example` must exist, be committed, and contain every variable that the application requires — with descriptive comments and safe placeholder values.
- Secrets must **never** appear in log output. Before logging any object that may contain user data or config, strip sensitive keys.

---

## 3. DEPENDENCY & SUPPLY CHAIN SECURITY

### 3.1 Version Pinning

Loose version ranges are a supply chain attack vector. A malicious or buggy patch release can silently enter the build.

**Scan for loose constraints in:**
| File | Dangerous patterns |
|---|---|
| `package.json` | `^`, `~`, `*`, `>=`, `>` |
| `requirements.txt` | `>=`, `~=`, no version specified |
| `go.mod` | `latest` pseudo-versions |
| `Cargo.toml` | `*`, `>=` without upper bound |
| `pyproject.toml` | `^`, `>=` without upper bound |

**Action:** Pin every dependency to an exact version.

```json
// ❌ Before
"express": "^4.17.0"

// ✅ After
"express": "4.18.2"
```

```
# ❌ Before
requests>=2.28.0

# ✅ After
requests==2.31.0
```

**After pinning:** Regenerate lockfiles to ensure consistency:
```bash
npm install          # regenerates package-lock.json
pip-compile          # regenerates requirements.txt from pyproject.toml
go mod tidy
cargo update
```

### 3.2 Known Vulnerability Check

Run the appropriate built-in audit tool for the detected package manager:

```bash
# Node.js
npm audit --audit-level=high

# Python (with pip-audit)
pip-audit

# Go
govulncheck ./...

# Rust
cargo audit
```

Any `HIGH` or `CRITICAL` vulnerability found here must be resolved. Check the advisory for the patched version, upgrade, and verify the fix is applied to the lockfile.

---

## 4. INPUT VALIDATION

**Rule:** Validate all data at the system boundary (HTTP endpoints, CLI args, queue consumers, file uploads). Trust nothing from outside the process. Reject invalid data immediately — do not sanitize and attempt to use it.

### 4.1 Validation Approach

Use a schema validation library appropriate to the stack. Do not write manual regex validation for structured types.

| Stack | Library |
|---|---|
| Python | Pydantic v2 |
| TypeScript / JavaScript | Zod |
| Go | `validator` package or manual with clear error returns |
| Rust | `serde` + `validator` crate |

Define schemas at the API boundary and parse incoming data through them before any business logic runs:

```typescript
// TypeScript — validate at the route handler boundary
const CreateUserSchema = z.object({
  email: z.string().email(),
  username: z.string().regex(/^[a-zA-Z0-9_]{3,32}$/, "Alphanumeric and underscores only"),
  age: z.number().int().min(13).max(120),
});

type CreateUserInput = z.infer<typeof CreateUserSchema>;

app.post("/users", (req, res) => {
  const result = CreateUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  // result.data is now typed and validated — safe to use
  createUser(result.data);
});
```

### 4.2 Allow-List Validation Patterns

When regex is appropriate (e.g., for free-form string fields), use strict allow-lists, not block-lists. Allow only what is explicitly expected.

| Field type | Pattern |
|---|---|
| Email | `^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$` |
| UUID v4 | `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$` |
| Username | `^[a-zA-Z0-9_]{3,32}$` |
| Slug | `^[a-z0-9\-]{1,64}$` |
| Numeric ID | `^\d{1,19}$` |

### 4.3 SQL Injection Prevention

Scan all database interaction code for string concatenation in queries.

```python
# ❌ Vulnerable — never do this
query = f"SELECT * FROM users WHERE email = '{email}'"
cursor.execute(query)

# ✅ Correct — parameterized query
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

**Action:** Every instance of dynamic SQL construction must be rewritten using parameterized queries or the ORM's query builder. No exceptions.

### 4.4 File Upload Validation

If the application accepts file uploads:
- Validate MIME type by inspecting file magic bytes, not just the filename extension or `Content-Type` header.
- Enforce a maximum file size limit.
- Store uploaded files outside the web root so they cannot be executed directly.
- Generate a random filename on storage; never use the user-supplied filename.

---

## 5. OUTPUT SANITIZATION & XSS PREVENTION

### 5.1 Framework-Specific Rules

**React:**
- `dangerouslySetInnerHTML` is **banned**. Remove every instance found.
- If rendering user-supplied rich text is a genuine product requirement, use `DOMPurify` with a strict allowlist:
  ```javascript
  import DOMPurify from 'dompurify';
  const clean = DOMPurify.sanitize(userHtml, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong'] });
  // Only then: <div dangerouslySetInnerHTML={{ __html: clean }} />
  ```

**Vue:**
- `v-html` is **banned**. Remove every instance. Apply the same DOMPurify approach if rich text rendering is required.

**Python / Jinja2:**
- Autoescaping must be enabled. Verify at template engine initialization:
  ```python
  # ✅ Correct
  env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
  ```
- The `| safe` filter must never be applied to user-supplied content.

**Django:**
- The `mark_safe()` function must never be called on user-supplied content.

### 5.2 Content-Type Headers

Every HTTP response must include an explicit `Content-Type` header. Browsers that receive a response without one will attempt content sniffing, which can enable XSS. The `X-Content-Type-Options: nosniff` header (see Phase 7) prevents this, but explicit `Content-Type` is still required.

---

## 6. AUTHENTICATION & SESSION HARDENING

### 6.1 Password Storage

| Algorithm | Status |
|---|---|
| `bcrypt` (cost ≥ 12) | ✅ Required |
| `argon2id` | ✅ Acceptable alternative |
| `scrypt` | ✅ Acceptable alternative |
| `PBKDF2` with SHA-256, ≥ 600,000 iterations | ✅ Acceptable (NIST current guidance) |
| `SHA-1`, `SHA-256`, `SHA-512` (unsalted or raw) | ❌ **DELETE and replace immediately** |
| `MD5` | ❌ **DELETE and replace immediately** |
| Any plaintext storage | ❌ **DELETE and replace immediately** |

**Action on finding a banned algorithm:** Replace with `bcrypt` (cost 12). Alert the user that **all existing hashed passwords are compromised** and a forced password reset must be issued.

### 6.2 Session Cookies

All session and auth cookies must carry these flags. Verify in the framework's session configuration, not ad-hoc on individual routes.

```
Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Strict; Path=/
```

| Flag | Purpose |
|---|---|
| `HttpOnly` | Prevents JavaScript access — blocks XSS-based token theft |
| `Secure` | Cookie only sent over HTTPS |
| `SameSite=Strict` | Prevents CSRF — cookie not sent on cross-site requests |
| `Path=/` | Scopes cookie to the full application |

### 6.3 JWT Hardening

If JWTs are used:
- Sign with `RS256` (asymmetric) or `HS256` with a secret of ≥ 256 bits. Never use `none` algorithm.
- Set a short expiry (`exp` claim) — 15 minutes for access tokens, 7 days maximum for refresh tokens.
- Validate `iss`, `aud`, and `exp` claims on every token verification.
- Never store JWTs in `localStorage`. Use `HttpOnly` cookies.

### 6.4 Multi-Factor Authentication (MFA)

If authentication is present and MFA is not yet implemented, add a checklist item noting it as a recommended hardening step. Do not implement MFA unprompted, but do surface the gap.

---

## 7. HTTP SECURITY HEADERS

Configure these headers at the server/middleware level so they apply to every response. Do not add them per-route.

| Header | Required Value | Purpose |
|---|---|---|
| `Content-Security-Policy` | See below | Prevent XSS and data injection |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Enforce HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer data leakage |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Restrict browser feature access |

**Content Security Policy — baseline value:**
```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';
```

> Note: If the application loads scripts or styles from CDNs, specific origins must be explicitly listed. Using `'unsafe-inline'` or `'unsafe-eval'` defeats the purpose of CSP and must not be added without a documented exception and a concrete plan to remove it.

**Implementation example (Express.js with Helmet):**
```javascript
import helmet from 'helmet';

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      objectSrc: ["'none'"],
      frameAncestors: ["'none'"],
    }
  },
  hsts: { maxAge: 63072000, includeSubDomains: true, preload: true },
}));
```

---

## 8. ERROR HANDLING & INFORMATION DISCLOSURE

Internal error details — stack traces, SQL queries, file paths, library versions — are a reconnaissance goldmine for attackers. They must never reach the client.

### 8.1 Response Rules

```javascript
// ❌ Leaks internal details
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.message, stack: err.stack });
});

// ✅ Safe — generic message to client, full details to internal log
app.use((err, req, res, next) => {
  logger.error({ err, requestId: req.id }); // Log full context internally
  res.status(500).json({ error: "An unexpected error occurred.", requestId: req.id });
});
```

### 8.2 Structured Logging

All errors must be logged internally with enough context to diagnose the issue:
- Timestamp (UTC, ISO 8601)
- Request ID (for correlation)
- User ID (if authenticated — hash or mask PII)
- Error type, message, and stack trace
- Relevant request metadata (method, path — never log request body wholesale)

Logs must be shipped to a centralized log aggregator. Files written to disk are acceptable only as a fallback.

### 8.3 404 vs. 401 vs. 403

Use correct HTTP status codes. Do not return `404` for an authenticated resource the user is not authorized to access — this leaks that the resource exists. Return `403 Forbidden` instead. Reserve `404` for resources that genuinely do not exist.

---

## 9. RATE LIMITING & ABUSE PREVENTION

Install rate-limiting middleware at the application layer. Do not rely solely on infrastructure-level rate limiting — defense in depth requires both.

### 9.1 Limits

| Endpoint / Context | Limit |
|---|---|
| Global (all routes) | 100 requests / 15 minutes per IP |
| Login / password reset | 5 requests / hour per IP |
| Account creation | 10 requests / hour per IP |
| API key authenticated routes | Set per customer tier in config |

### 9.2 Implementation

**Express.js:**
```javascript
import rateLimit from 'express-rate-limit';

const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: "Too many requests. Please try again later." },
});

const loginLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 5,
  message: { error: "Too many login attempts. Please try again later." },
});

app.use(globalLimiter);
app.post("/auth/login", loginLimiter, loginHandler);
app.post("/auth/reset-password", loginLimiter, resetHandler);
```

**Python (FastAPI):**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/hour")
async def login(request: Request, credentials: LoginCredentials):
    ...
```

### 9.3 Additional Abuse Controls

- Return `429 Too Many Requests` with a `Retry-After` header on limit breach.
- Implement exponential backoff on repeated failed authentication (not just rate limits).
- Log all rate limit hits for anomaly detection.

---

## 10. AUTOMATED SECURITY SCANNING

These scans are **mandatory**. The task is not complete until both scanners have run and all `HIGH` and `CRITICAL` findings are resolved or documented with a formal exception.

### 10.1 Trivy — Filesystem, Vulnerability & Misconfiguration Scan

```bash
# Run from the repository root
trivy fs . \
  --scanners vuln,secret,misconfig \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  --format table
```

**Interpreting results:**

| Exit code | Meaning | Action |
|---|---|---|
| `0` | No HIGH/CRITICAL findings | Proceed to Snyk |
| `1` | Findings detected | **STOP.** Read every finding. Fix or formally document each one before proceeding. |

**For each finding:**
- **Vulnerability (CVE):** Upgrade the affected package to the patched version listed in the advisory. Re-run Trivy to confirm resolution.
- **Secret detected:** Treat as a live credential leak. Follow Phase 2.2 immediately.
- **Misconfiguration:** Fix the configuration issue as described in the Trivy output. Common examples: world-readable file permissions, insecure Dockerfile instructions, missing security contexts in Kubernetes manifests.

### 10.2 Snyk — Dependency & Code Vulnerability Scan

**Prerequisite:** `SNYK_TOKEN` must be set. If not, see Phase 1.2 warning.

```bash
# Scan all projects for dependency vulnerabilities
snyk test --all-projects --severity-threshold=high

# Scan source code for security issues
snyk code test --severity-threshold=high
```

**Interpreting results:**

| Finding type | Action |
|---|---|
| Vulnerable dependency | Upgrade to the version specified in the Snyk advisory. If no fix is available, check for an alternative package and document the exception. |
| Code vulnerability | Fix the code pattern identified by Snyk. Common examples: insecure deserialization, path traversal, hardcoded credentials. |

**When a fix is not immediately available:**
1. Document the finding in a `SECURITY_EXCEPTIONS.md` file with: CVE ID or Snyk ID, affected component, severity, reason fix is deferred, and a target remediation date.
2. Ensure the exception is reviewed and approved before the task is marked complete.

---

## 11. FINAL VERIFICATION CHECKLIST

Complete every item before closing the task. Any unchecked item is a blocker.

#### Secrets & Filesystem
- [ ] `.env` is present in `.gitignore`
- [ ] `.env.example` exists and documents all required variables with safe placeholders
- [ ] No hardcoded secrets, tokens, or credentials found in source code
- [ ] No dangerous file types (`.pem`, `.key`, `.db`, `.log`) committed to the repository

#### Dependencies
- [ ] All dependencies pinned to exact versions
- [ ] Lockfiles regenerated and committed after pinning
- [ ] Built-in audit tool run (`npm audit` / `pip-audit` / `govulncheck` / `cargo audit`) with no HIGH/CRITICAL findings

#### Input & Output
- [ ] All external inputs validated through a schema library at the API boundary
- [ ] No raw string concatenation in SQL queries
- [ ] `dangerouslySetInnerHTML` / `v-html` / `| safe` removed or wrapped with sanitization
- [ ] Jinja2 / Django autoescaping confirmed enabled

#### Authentication & Sessions
- [ ] Passwords hashed with bcrypt (cost ≥ 12) or Argon2id — no MD5/SHA1
- [ ] Session cookies have `HttpOnly`, `Secure`, `SameSite=Strict` flags
- [ ] JWTs validated for `alg`, `iss`, `aud`, `exp` on every request (if applicable)

#### Network & Headers
- [ ] All required HTTP security headers configured at the middleware level
- [ ] CSP does not use `'unsafe-inline'` or `'unsafe-eval'` without a documented exception
- [ ] Rate limiting active on global routes and sensitive endpoints

#### Error Handling
- [ ] No stack traces or internal error details returned to the client
- [ ] All errors logged internally with request context

#### Automated Scans
- [ ] **Trivy scan passed** — zero HIGH/CRITICAL findings (or all findings documented in `SECURITY_EXCEPTIONS.md`)
- [ ] **Snyk scan passed** — zero HIGH/CRITICAL findings (or all findings documented in `SECURITY_EXCEPTIONS.md`), if `SNYK_TOKEN` is available

---

*This protocol is versioned. Propose changes via a pull request with a security justification. Do not modify this file unilaterally.*
