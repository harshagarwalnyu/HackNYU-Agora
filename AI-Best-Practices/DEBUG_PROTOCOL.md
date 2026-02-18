# DEBUG_PROTOCOL.md v1.0

> **Role:** Debugging Agent. Execute the Scientific Method, not trial-and-error.
> **Priority:** Root cause identification > Symptom treatment. Band-aids are forbidden.
> **Posture:** SYSTEMATIC. Do not guess. Do not retry the same fix twice. Do not move on until you understand *why* the bug occurred.
> **Blocking Rule:** If you have attempted the same fix three times, **STOP** and execute the Escalation Protocol (Phase 9).

---

## TABLE OF CONTENTS

1. [Pre-Debug Cognitive Routine](#1-pre-debug-cognitive-routine)
2. [Information Gathering](#2-information-gathering)
3. [Hypothesis Formation](#3-hypothesis-formation)
4. [Reproduction & Isolation](#4-reproduction--isolation)
5. [Instrumentation & Observability](#5-instrumentation--observability)
6. [Root Cause Analysis](#6-root-cause-analysis)
7. [Fix Implementation & Verification](#7-fix-implementation--verification)
8. [Regression Prevention](#8-regression-prevention)
9. [Escalation Protocol](#9-escalation-protocol)
10. [Language-Specific Debugging Patterns](#10-language-specific-debugging-patterns)
11. [Final Debug Report](#11-final-debug-report)

---

## 1. PRE-DEBUG COGNITIVE ROUTINE

Execute these steps **before touching any code**. Debugging without context is guessing.

### Step 1 — Verify the Bug Report

Do not trust the initial description at face value. Users describe symptoms, not causes.

**Questions to answer:**
- What is the **exact** error message or unexpected behavior? (Copy it verbatim.)
- What was the user trying to accomplish when it failed?
- Can the user provide steps to reproduce? If yes, document them. If no, reproduction is Phase 4.
- Is this a new bug (regression) or has it always been broken?
- What changed recently? (Code deploy, dependency upgrade, config change, data migration, infrastructure change)

### Step 2 — Establish Current State

Confirm the actual state of the system before making assumptions.

```bash
# Check file existence
ls -la path/to/suspected/file

# Verify service status
systemctl status service-name  # or Docker ps, k8s get pods, etc.

# Check environment variables
printenv | grep RELEVANT_VAR

# Verify dependency versions
npm list package-name  # or pip show, go list, cargo tree
```

**Do not proceed** if your mental model of "what should be there" conflicts with what actually exists. Reconcile the discrepancy first.

### Step 3 — Check the Obvious First

**80% of bugs are caused by:**
1. Typos in variable names, function calls, or import paths
2. Null/undefined values where non-null was expected
3. Off-by-one errors in loops or array indexing
4. Incorrect comparison operators (`=` instead of `==`, `==` instead of `===`)
5. Asynchronous code treated as synchronous (missing `await`)
6. Cached stale data (browser cache, Redis, CDN, DNS)
7. Wrong environment or configuration loaded

Scan for these first. Do not skip this step to look for "interesting" bugs.

### Step 4 — Read the Full Error Trace

If an error or stack trace is available, **read the entire thing from top to bottom** before acting.

**Extract:**
- The root exception type and message
- The file and line number where the error originated (not where it was caught)
- The call stack leading to the error
- Any logged context variables or request IDs

Do not read only the first line and guess. The root cause is often buried 10 lines down.

---

## 2. INFORMATION GATHERING

Collect all available evidence before forming a hypothesis. Missing one piece of data can send you down a false path.

### 2.1 Logs

Pull logs for the relevant time window. If request IDs or trace IDs are available, filter by them.

```bash
# Tail live logs with relevant filter
tail -f /var/log/app.log | grep "ERROR\|WARN"

# Pull structured logs from the last hour
journalctl -u service-name --since "1 hour ago" --no-pager

# Query centralized logging (example: Datadog, Splunk)
# Filter: service:api-service status:error time:[now-1h TO now]
```

**Look for:**
- Errors immediately before the reported failure
- Warnings that were ignored but indicate degraded state
- Timing anomalies (a request that took 30 seconds instead of 200ms)
- Resource exhaustion signals (out of memory, connection pool full, disk full)

### 2.2 Monitoring & Metrics

Check system health metrics for the time window when the bug occurred.

| Metric | What to look for |
|---|---|
| CPU usage | Sustained 100% → blocking operation or infinite loop |
| Memory usage | Gradual climb → memory leak; sudden spike → large allocation |
| Network I/O | High outbound → API retry storm; low → connectivity issue |
| Database query time | Sudden spike → missing index, lock contention |
| HTTP status codes | 5xx spike → server error; 4xx spike → client validation failing |
| Queue depth | Growing → consumer slower than producer |

### 2.3 Recent Changes

Pull the git log for the last 7 days (or since the last known-good state).

```bash
# Show commits and changed files
git log --oneline --since="7 days ago" --stat

# Show full diff of recent changes to a specific file
git log -p --since="7 days ago" -- path/to/file.py
```

**Compare:** If the bug is a regression, `git bisect` can identify the exact commit that introduced it. Use it.

```bash
git bisect start
git bisect bad HEAD              # current state is broken
git bisect good v1.2.3          # known working version
# Git will checkout a commit; test it, then mark:
git bisect good  # if it works
git bisect bad   # if it fails
# Repeat until Git identifies the breaking commit
```

### 2.4 External Dependencies

Check the status of external services.

```bash
# DNS resolution
nslookup api.external-service.com

# Network connectivity
curl -I https://api.external-service.com/health

# SSL certificate validity
openssl s_client -connect api.external-service.com:443 -servername api.external-service.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

If the service has a public status page, check it. If there was a recent outage or degradation, that may be the root cause.

---

## 3. HYPOTHESIS FORMATION

A hypothesis is a testable, falsifiable statement about the cause of the bug. It is **not** a guess.

### 3.1 Structure of a Hypothesis

A valid hypothesis has three parts:

1. **Observation:** "When X happens, Y fails."
2. **Proposed cause:** "I believe this is because Z."
3. **Test:** "If I do A, I expect to observe B."

**Example:**
- **Observation:** The API returns 500 when the email field is empty.
- **Proposed cause:** The email validation function does not handle `null` input.
- **Test:** Add a log statement inside the validation function. If the log shows `email = null`, the hypothesis is supported.

### 3.2 Prioritize Hypotheses

If you have multiple hypotheses, rank them by:
1. **Likelihood** (based on evidence)
2. **Impact** (does this explain the entire bug or just one symptom?)
3. **Ease of testing** (can you verify this in under 5 minutes?)

Test the highest-ranked hypothesis first. Do not test all hypotheses simultaneously; you will not know which change fixed it.

### 3.3 Anti-Patterns to Avoid

**Do not form hypotheses like:**
- "It's probably a caching issue" → too vague, not testable
- "Maybe if I restart the server it will work" → not a hypothesis, just hope
- "I'll just try changing this and see what happens" → not systematic

---

## 4. REPRODUCTION & ISOLATION

If you cannot reproduce the bug reliably, you cannot verify that you fixed it. Reproduction is **non-negotiable**.

### 4.1 Minimal Reproduction

Create the smallest possible environment that triggers the bug. Strip away everything unrelated.

**Steps:**
1. Start with the reported failing case.
2. Remove one variable (auth, database, external API, etc.) and retest.
3. If it still fails, that variable was not the cause — remove the next one.
4. Repeat until you have the minimal set of conditions that trigger the bug.

**Example:**
```
Initial: "Bug occurs when user with role=admin creates an invoice with discount > 50%"
After isolation: "Bug occurs any time discount > 50%, regardless of user role"
Root cause: The discount validation logic has a boundary condition error at 50%.
```

### 4.2 Isolation Techniques

| Technique | When to use |
|---|---|
| Unit test | Bug is in pure business logic with no external dependencies |
| Integration test | Bug involves interaction between two components (API + DB) |
| Local script | Bug is in a data processing pipeline — replicate with sample data |
| Docker container | Bug is environment-specific — reproduce the prod environment locally |
| Debugger breakpoint | Bug is in control flow or state mutation |

### 4.3 Environment Parity

If the bug only occurs in production, not locally, the **environment is the variable**. Identify the differences:

| Factor | How to check |
|---|---|
| Environment variables | Compare `.env` vs production config |
| Dependency versions | Compare lockfiles vs deployed container |
| Data volume | Production has 1M records, local has 100 |
| Network latency | Production calls APIs across regions, local is on localhost |
| Operating system | Linux vs macOS file path case sensitivity |
| Clock drift / time zones | Timestamp comparison bugs |

Replicate the production environment factor-by-factor until the bug reproduces locally.

---

## 5. INSTRUMENTATION & OBSERVABILITY

If you cannot see what the code is doing, you are debugging blind. Add instrumentation before guessing.

### 5.1 Strategic Logging

Add log statements at critical decision points. Log the actual values, not just "got here."

```python
# ❌ Useless
logger.info("Processing payment")

# ✅ Useful — log the state
logger.info(f"Processing payment: amount={amount}, currency={currency}, user_id={user_id}")
```

**Where to log:**
- Function entry: log all input arguments
- Before conditional branches: log the variables being evaluated
- Before external calls: log request parameters
- After external calls: log response status and key fields
- Function exit: log the return value

### 5.2 Debugger Usage

Use an interactive debugger to pause execution and inspect state in real time.

| Language | Debugger | How to set breakpoint |
|---|---|---|
| Python | `pdb` / `ipdb` | Add `import pdb; pdb.set_trace()` or `breakpoint()` |
| JavaScript | Chrome DevTools / VS Code | Add `debugger;` statement or use IDE breakpoints |
| Go | `delve` | `dlv debug` then `break main.functionName` |
| Rust | `lldb` / `gdb` | Compile with debug symbols, `rust-lldb ./target/debug/app` |

**When paused, inspect:**
- Local variables: `p variable_name`
- Call stack: `bt` (backtrace)
- Step through: `n` (next line), `s` (step into function), `c` (continue)

### 5.3 Profiling & Tracing

For performance bugs (slowness, timeouts, high resource usage), use a profiler.

**Python:**
```python
import cProfile
cProfile.run('expensive_function()', sort='cumtime')
```

**Node.js:**
```bash
node --inspect app.js
# Open chrome://inspect, capture CPU profile
```

**Go:**
```go
import _ "net/http/pprof"
// Then: go tool pprof http://localhost:6060/debug/pprof/profile
```

**Look for:**
- Functions consuming disproportionate CPU time
- Repeated allocations in a loop
- Blocking I/O that should be async

### 5.4 Network Inspection

For API bugs, inspect the actual HTTP requests and responses.

```bash
# Proxy all HTTP through mitmproxy
mitmproxy --mode reverse:http://api.example.com

# Capture with curl
curl -v https://api.example.com/endpoint

# Inspect WebSocket frames
wscat -c wss://api.example.com/ws
```

Verify:
- Request headers (auth tokens, content-type)
- Request body (is the payload actually what you expect?)
- Response status code
- Response body (error details often buried in JSON)

---

## 6. ROOT CAUSE ANALYSIS

Once you have reproduction and observability, identify the **root cause**, not just the proximate cause.

### 6.1 The "5 Whys" Technique

Ask "why" five times to drill down from symptom to root cause.

**Example:**
1. **Why** did the user see a blank page? → Because the API returned 500.
2. **Why** did the API return 500? → Because the database query timed out.
3. **Why** did the query time out? → Because it was missing an index on the `created_at` column.
4. **Why** was the index missing? → Because the migration script failed to run in production.
5. **Why** did the migration fail? → Because the deploy pipeline skipped the migration step when env=production.

**Root cause:** Deploy pipeline configuration error.
**Fix:** Update pipeline to run migrations in all environments.

### 6.2 Distinguish Cause from Symptom

| Symptom | Root Cause |
|---|---|
| API returns 500 | Database connection pool exhausted |
| User logout fails | CSRF token expired |
| Page loads slowly | Missing database index on frequently queried column |
| File upload fails | Disk full on server |
| Websocket disconnects | Reverse proxy timeout too short |

**Test:** If you fix the symptom but not the root cause, the bug will return or manifest in a different form.

### 6.3 Document Your Findings

Before implementing a fix, write down:
1. What the code **currently** does (the buggy behavior)
2. What the code **should** do (the correct behavior)
3. **Why** the current implementation is wrong (the logic flaw, the missing validation, the race condition, etc.)
4. What you will change to fix it

This documentation becomes part of the commit message and, for complex bugs, an ADR or postmortem.

---

## 7. FIX IMPLEMENTATION & VERIFICATION

### 7.1 Surgical Fixes

Change **only** what is necessary to resolve the root cause. Do not:
- Refactor unrelated code in the same commit
- "Improve" nearby code that is working
- Introduce new abstractions unless the bug reveals a design flaw that requires it

### 7.2 Fix Validation Checklist

Before committing the fix, verify:

- [ ] The minimal reproduction case now passes
- [ ] No existing tests are broken
- [ ] A new test has been added that fails on the buggy code and passes on the fixed code
- [ ] The fix does not introduce new edge cases (e.g., fixing null but breaking empty string)
- [ ] Logging or instrumentation added during debugging has been **removed or reduced to appropriate level** (debug logs should not spam production)

### 7.3 Test the Fix

Run the test suite **locally** before pushing.

```bash
# Python
pytest tests/ -v

# JavaScript
npm test

# Go
go test ./... -v

# Rust
cargo test
```

If the bug was environment-specific, verify the fix in a **staging environment** that mirrors production before deploying.

### 7.4 Avoid "Fix by Suppression"

These are not fixes:
- Wrapping the error in a `try/catch` without handling it
- Adding `|| null` to silence a type error
- Increasing a timeout without understanding why the operation is slow
- Disabling a linter rule that caught the bug

If you cannot fix the root cause immediately, document the suppression with a `TODO` linking to a tracking issue and an explanation of why it is safe to suppress in the interim.

---

## 8. REGRESSION PREVENTION

A bug that happens once will happen again unless you build defenses.

### 8.1 Add a Regression Test

Every bug fix **must** be accompanied by a test that:
1. Would have caught the bug before it shipped
2. Will catch it if someone accidentally reintroduces it

The test should live in the test suite, not as a one-off script.

```python
def test_discount_validation_rejects_above_50_percent():
    """Regression test for bug #1234: discount validation boundary error."""
    with pytest.raises(ValidationError):
        validate_discount(51)  # Should reject, was incorrectly accepted
```

### 8.2 Improve Observability

If debugging was difficult because of missing logs or metrics, **add them now** before you forget.

- Add a log statement at the error site with relevant context
- Add a metric counter for this error type (`payment.validation_error`)
- Add a trace span around the slow operation

### 8.3 Update Documentation

If the bug was caused by misunderstanding or misusing an API:
- Update the docstring to clarify the expected input
- Add an example of correct usage
- Add a warning about the failure mode

### 8.4 Consider a Linter Rule

If the bug was caused by a pattern that a linter could catch (e.g., using `==` instead of `===`), enable the rule.

| Bug pattern | Linter rule |
|---|---|
| Using `==` instead of `===` | `eqeqeq` (ESLint) |
| Unused variables | `unused-variable` (Pylint) |
| Missing error handling | `errcheck` (Go) |
| Unwrap on Result | `clippy::unwrap_used` (Rust) |

---

## 9. ESCALATION PROTOCOL

If you are stuck, **do not loop indefinitely**. Follow this protocol.

### 9.1 The Three-Attempt Rule

If you have tried the **same approach** three times with no progress, you are stuck. Execute the escalation steps.

### 9.2 Escalation Steps

#### Step 1 — Restate the Problem
Write out, in plain language:
- What you know
- What you have tried
- What you expected vs. what you observed
- What you are currently confused about

The act of writing this often reveals the missing piece.

#### Step 2 — Rubber Duck Debugging
Explain the bug out loud to an inanimate object (or to yourself). Walk through the code line by line, explaining what each line does.

If you hear yourself say "...and then it does something, I'm not sure what," you have found the knowledge gap. Investigate that line.

#### Step 3 — Consult External Resources

Search for the **exact error message** in quotes:
```
"KeyError: 'user_id'" python
"cannot read property of undefined" javascript
```

Check:
- GitHub issues in the library's repository
- Stack Overflow (sort by votes, read accepted answers)
- Official documentation for the library or framework

### 9.3 Escalate to Human

If none of the above resolves it, surface the issue to the user with this format:

```
**Bug:** [Brief description]

**What I've tried:**
1. [Approach 1] — Result: [What happened]
2. [Approach 2] — Result: [What happened]
3. [Approach 3] — Result: [What happened]

**Current hypothesis:**
[Your best current theory about the cause]

**What I need:**
- Clarification on [specific ambiguity]
- Access to [specific resource, log, environment]
- OR: A different pair of eyes on [specific file/function]

**Relevant context:**
- Error message: [paste full trace]
- Code snippet: [link or paste]
- Attempted fix: [diff or description]
```

Do not just say "I'm stuck." Provide enough context that the human can jump in without retracing all your steps.

---

## 10. LANGUAGE-SPECIFIC DEBUGGING PATTERNS

### 10.1 Python

**Common pitfalls:**
- Mutable default arguments: `def func(items=[])`
- Late binding in closures: functions in a loop all reference the same variable
- Circular imports causing `AttributeError`
- `is` vs `==` confusion

**Debugging tools:**
```python
# Interactive debugging
breakpoint()  # Python 3.7+

# Inspect object attributes
dir(obj)
vars(obj)

# Check type
type(variable)
isinstance(variable, ExpectedType)

# Trace function calls
import trace
tracer = trace.Trace(count=False, trace=True)
tracer.run('function_call()')
```

### 10.2 JavaScript / TypeScript

**Common pitfalls:**
- `this` binding issues in callbacks
- Promises not awaited or `.catch()` missing
- Race conditions in async code
- Truthy/falsy confusion (`0`, `""`, `null`, `undefined` all falsy)
- Mutation of state in React causing stale renders

**Debugging tools:**
```javascript
// Pause execution
debugger;

// Check type
typeof variable
Array.isArray(variable)
variable instanceof ClassName

// Trace async issues
console.trace();

// Deep clone to avoid reference issues
const copy = JSON.parse(JSON.stringify(obj));

// React DevTools: inspect component props and state
```

### 10.3 Go

**Common pitfalls:**
- Ignoring errors (`err != nil`)
- Goroutine leaks (no cleanup path)
- Sending to a closed channel
- Data races (use `go run -race`)
- Pointer vs value receiver confusion

**Debugging tools:**
```bash
# Race detector
go run -race main.go

# Delve debugger
dlv debug
> break main.processRequest
> continue
> print variableName

# Check for goroutine leaks
GODEBUG=gctrace=1 go run main.go
```

### 10.4 Rust

**Common pitfalls:**
- Borrowing rules (mutable borrow while immutable borrow exists)
- Moving a value then trying to use it
- Lifetime mismatches in structs
- Panic in production code (`.unwrap()`)
- Integer overflow in release mode

**Debugging tools:**
```bash
# Enable backtraces
RUST_BACKTRACE=1 cargo run

# Overflow checks in release mode
RUSTFLAGS="-C overflow-checks=on" cargo build --release

# LLDB debugger
rust-lldb ./target/debug/app
> breakpoint set --name function_name
> run
> frame variable
```

---

## 11. FINAL DEBUG REPORT

Document your debugging process in the commit message or a postmortem (for critical bugs).

### 11.1 Commit Message Format

```
fix: prevent null pointer in payment validation

**Root cause:**
The validatePaymentMethod function did not check for null input
before accessing the `type` property, causing a crash when users
submitted a form without selecting a payment method.

**Fix:**
Added null check at function entry. If input is null, return
early with a validation error instead of attempting to access
properties.

**Testing:**
- Added regression test: test_payment_validation_rejects_null_input
- Verified fix in staging with manual form submission

Closes #1234
```

### 11.2 Postmortem Template (for Critical Bugs)

For bugs that caused an outage, data loss, or security incident:

```markdown
# Postmortem: [Brief Title]

**Date:** 2025-01-15
**Duration:** 14:23 UTC - 15:47 UTC (1h 24m)
**Impact:** API unavailable for 30% of requests, affecting ~5,000 users

## Timeline
- 14:23 — First alert: API error rate spike
- 14:30 — On-call engineer began investigation
- 14:45 — Root cause identified: database connection pool exhausted
- 15:10 — Fix deployed: increased pool size from 10 to 50
- 15:47 — Error rate returned to baseline

## Root Cause
[Detailed explanation of what went wrong and why]

## Resolution
[What was changed to fix it]

## Prevention
1. [Action item 1: e.g., add connection pool monitoring]
2. [Action item 2: e.g., load test before deploy]
3. [Action item 3: e.g., update runbook]

## Lessons Learned
- [What we learned from this incident]
```

### 11.3 Knowledge Base Entry

For bugs that may recur or that other developers may encounter, add an entry to a `docs/troubleshooting.md`:

```markdown
## Payment validation crashes on null input

**Symptom:** API returns 500 when payment method is not selected

**Cause:** Missing null check in `validatePaymentMethod`

**Fix:** Upgrade to v1.2.3+ or add null guard:
\`\`\`python
if payment_method is None:
    raise ValidationError("payment method required")
\`\`\`

**Reference:** Issue #1234, PR #1235
```

---

*This protocol is versioned. Suggest improvements via pull request with examples of bugs it would have helped debug faster.*
