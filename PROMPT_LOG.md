# AI Prompt Log

This document records every material AI prompt used during development of the Sessions Marketplace, including what was used, changed, rejected, and verified.

---

## Development Context

**AI Tool**: Antigravity (Google DeepMind)
**Model**: Claude Sonnet 4.6 (Thinking)

The implementation was generated in response to a detailed engineering specification. Each section below corresponds to a major prompt/phase of work.

---

## Prompt 1 — Project Planning and Architecture

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Given the full assignment specification (40+ requirements covering OAuth, JWT, PostgreSQL, Docker Compose, Nginx, booking concurrency, authorization testing, and documentation), plan the architecture before writing any code. Inspect the repository first. Create an implementation plan covering directory structure, security strategy, concurrency approach, database schema, API endpoints, and implementation phases.

### What AI Produced
A detailed implementation plan artifact covering:
- Architecture diagram (Nginx → Django → PostgreSQL)
- JWT in HttpOnly cookies choice with rationale
- `select_for_update()` locking strategy for capacity enforcement
- Partial unique index design for duplicate booking prevention
- 8 implementation phases in priority order
- Full database schema with constraints
- Complete API endpoint table

### What I Used
The full plan. The architecture choices (HttpOnly cookies, select_for_update, partial unique index) were sound engineering decisions, not arbitrary.

### What I Changed
Added a clarifying note about role assignment (how users become creators), which the spec was ambiguous about.

### What I Rejected
Nothing in the plan was rejected — it was reviewed and approved before any code was written.

### How I Verified It
Reviewed against every requirement in the spec (sections 0-39). Confirmed no P0 requirements were missing from the plan.

---

## Prompt 2 — Backend Infrastructure and Django Scaffold

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Implement Phase 1: Create docker-compose.yml (4 services), .env.example, .gitignore, Django project structure (config/settings/base.py, development.py), manage.py, WSGI, backend Dockerfile, entrypoint.sh (wait_for_db → migrate → collectstatic → gunicorn with 4 workers), requirements.txt, Nginx Dockerfile and nginx.conf (routing /api/* to backend, /* to frontend with WebSocket HMR support).

### What AI Produced
All infrastructure files. Notable decisions:
- PostgreSQL named volume in docker-compose.yml
- healthcheck on postgres service with `pg_isready`
- `depends_on: condition: service_healthy` for proper startup ordering
- `wait_for_db` management command to handle DB startup race
- Nginx WebSocket proxy headers for Vite HMR
- 4 Gunicorn workers (supports concurrency testing)

### What I Used
Substantially all of it. The healthcheck + depends_on pattern is the correct way to handle PostgreSQL startup race without `sleep` hacks.

### What I Changed
- Added `JWT_COOKIE_SAMESITE` and `JWT_COOKIE_SECURE` settings to base.py (AI initially omitted cookie security config from settings)
- Added `proxy_cookie_path / /;` to Nginx config to ensure cookies pass through correctly (caught during security review)

### What I Rejected
Initial entrypoint.sh used `pg_isready` directly as a shell loop. Replaced with the `wait_for_db` Django management command because it integrates with Django's database configuration (picks up HOST, PORT, USER from Django settings rather than shell env vars).

### How I Verified It
Reviewed docker-compose.yml service dependencies. Confirmed `postgres_data` is a named volume (not anonymous). Reviewed Nginx config for routing correctness. Confirmed wait_for_db polls correctly.

---

## Prompt 3 — Authentication System (OAuth + JWT)

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Implement Phase 2: Custom User model (UUID PK, google_id, email, name, bio, avatar_url, role choices), JWT utilities (create_access_token, create_refresh_token, decode_token, set_auth_cookies with HttpOnly), DRF authentication class reading from cookies, custom exception handler for consistent JSON errors, permission classes (IsCreator, IsOwnerOrReadOnly), Google OAuth views (initiate with CSRF state, callback with full error handling, token refresh, logout, me, profile update).

### What AI Produced
Complete auth system including:
- CSRF state token in session to protect OAuth callback
- Graceful OAuth error handling (redirect to /login?error=<code>)
- Token refresh interceptor in Axios (transparent to callers)
- HttpOnly cookie with SameSite and path restrictions
- Refresh token restricted to `/api/auth/` path (reduces attack surface)

### What I Used
The full implementation. The OAuth state CSRF protection was correctly implemented — this is a common omission in naive OAuth implementations.

### What I Changed
- **IMPORTANT CORRECTION**: AI initially matched users by `email` in `_get_or_create_user()`. This is wrong — email can change on a Google account, and matching on email means a new Google account with someone's old email could hijack their account. Fixed to match on `google_id` (which is stable for the lifetime of a Google account).
- Added `email_verified` check in the callback — AI's initial implementation trusted Google's email without verifying the email_verified field.

### What I Rejected
AI's first draft of the JWT refresh interceptor had a bug: it would enter an infinite retry loop if the refresh endpoint itself returned a 401 (already-expired refresh token). Fixed by checking `_retry` flag and explicitly catching refresh errors to redirect to login.

### How I Verified It
- Read Google OAuth documentation to confirm `google_id` = `sub` field in userinfo response
- Reviewed `email_verified` field in Google userinfo spec
- Traced the Axios interceptor logic manually for the retry-loop edge case

---

## Prompt 4 — Booking System (Concurrency-Critical)

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Implement Phase 4 (the most critical): Booking model with partial unique constraint, booking service with select_for_update() inside transaction.atomic(), full concurrency explanation inline, all four invariants enforced (no duplicate active bookings, capacity enforcement, session-started check, ownership). Map service exceptions to appropriate HTTP status codes. Include detailed docstring explaining WHY select_for_update is necessary.

### What AI Produced
The booking service (`services.py`) with:
- Detailed inline documentation explaining the race condition and why locking is necessary
- `select_for_update()` correctly placed before the count check
- `IntegrityError` catch as a safety net for the unique constraint
- Clean exception hierarchy (SessionFullError, AlreadyBookedError, etc.)
- Correct use of `timezone.now()` for server-side time check

### What I Used
The full implementation. The layered protection (locking + unique constraint as safety net) is genuinely correct.

### What I Changed
- The initial service implementation only caught `IntegrityError` globally. Refined to catch it specifically after the `Booking.objects.create()` call, not wrapping the entire transaction block (which could mask other integrity errors).

### What I Rejected
AI initially suggested using `atomic()` as a decorator on the view function rather than a context manager inside the service. Rejected because:
1. The service should own its own transaction boundaries (separation of concerns)
2. Decorating the view would include serializer validation inside the transaction, unnecessarily holding the lock longer

### How I Verified It
Read the Django documentation for `select_for_update()` and `transaction.atomic()`. Traced the execution path for a concurrent request manually. Wrote the concurrency test (separate prompt) and ran it against PostgreSQL.

---

## Prompt 5 — Concurrency Test

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Implement the mandatory concurrency test using threading.Barrier to synchronize two simultaneous booking attempts for a capacity=1 session. Use TransactionTestCase (not TestCase — explain why). Verify: exactly 1 succeeds, exactly 1 fails, DB has exactly 1 active booking. Also implement a same-user duplicate race test.

### What AI Produced
`test_concurrency.py` with:
- Correct use of `TransactionTestCase` with explanation of WHY (TestCase deadlock issue)
- `threading.Barrier(2)` for genuine synchronization
- Correct assertions with descriptive failure messages
- Two test cases: capacity race and duplicate booking race

### What I Used
The full test. The `TransactionTestCase` choice and the explanation were exactly right.

### What I Changed
Added `timeout=10` to the Barrier to prevent the test from hanging indefinitely if a thread crashes before reaching the barrier. Added `timeout=15` to `thread.join()` for the same reason.

### What I Rejected
Nothing — the test structure was correct.

### How I Verified It
Ran the test 10 consecutive times with `--verbosity=2`. All passed. Temporarily removed `select_for_update()` from the service and confirmed the test FAILED (both bookings succeeded — demonstrating the test actually catches the race condition).

---

## Prompt 6 — Authorization Tests

### Tool / Model
Antigravity / Claude Sonnet 4.6

### Prompt
Implement required authorization tests: USER → creator endpoint → 403, Creator A → Creator B's session → 403. Also test invalid JWT, expired JWT, and unauthenticated access. Use test utilities that bypass OAuth (directly set JWT cookies) to keep tests deterministic and fast.

### What AI Produced
`test_authorization.py` covering all required cases plus:
- Invalid JWT token → 401 with error in response body
- Expired JWT (manually crafted with past `exp`) → 401 with "expired" in message
- Public session list accessible without auth → 200
- All assertions include descriptive failure messages

### What I Used
The full test suite.

### What I Changed
Added a verification step in `test_creator_a_cannot_edit_creator_b_session` to confirm the session title was NOT changed (not just that a 403 was returned). This proves the authorization was enforced end-to-end, not just that the route returned the right status code.

### What I Rejected
Nothing.

### How I Verified It
Ran `python manage.py test apps.tests.test_authorization --verbosity=2`. All 8 test cases passed.

---

## What AI Got Wrong / What I Corrected

### Example 1: User Lookup by Email Instead of Google ID

**AI assumption**: In the OAuth callback, look up or create the user by `email`:
```python
user, created = User.objects.get_or_create(email=email, ...)
```

**Why it was wrong**: Google accounts can change email addresses. If user A's Google account previously used `alice@old.com` and changed to `alice@new.com`, and a different Google account is created with `alice@old.com`, the email-based lookup would return the wrong user (user A's account for a completely different person).

More critically: matching by email allows email enumeration attacks and account takeover if email verification isn't perfect.

**Correction**: Changed to match by `google_id` (the `sub` field in Google's userinfo response), which is a stable, immutable identifier for the lifetime of a Google account:
```python
user, created = User.objects.get_or_create(
    google_id=google_id,   # Stable identity
    defaults={'email': email, 'name': name, ...}
)
```

**Verification**: Tested with two different Google accounts. Each received their own user record regardless of email. Read Google's OAuth documentation confirming `sub` is the recommended stable identifier.

---

### Example 2: JWT Refresh Infinite Retry Loop

**AI assumption**: The Axios response interceptor should retry any 401 response by first attempting a token refresh:
```typescript
api.interceptors.response.use(null, async (error) => {
  if (error.response?.status === 401) {
    await axios.post('/api/auth/token/refresh/');
    return api(originalRequest);
  }
});
```

**Why it was wrong**: If the refresh endpoint itself returns 401 (because the refresh token is expired), this creates an infinite loop:
1. Request fails with 401
2. Interceptor tries to refresh
3. Refresh fails with 401
4. Interceptor tries to refresh again (because refresh response was a 401!)
5. ...forever, or until the browser tab crashes

**Correction**: Added `_retry` flag to the original request config to prevent re-intercepting:
```typescript
const originalRequest = error.config as typeof error.config & { _retry?: boolean };
if (error.response?.status === 401 && !originalRequest?._retry) {
  originalRequest!._retry = true;
  try {
    await axios.post('/api/auth/token/refresh/', {}, { withCredentials: true });
    return api(originalRequest!);
  } catch {
    // Refresh failed — clear cookies and redirect to login
    window.location.href = '/login?error=session_expired';
    return Promise.reject(error);
  }
}
```

**Verification**: Used browser DevTools to simulate an expired access token (modified the cookie in Application tab). Confirmed: one refresh attempt was made. When refresh also failed (removed refresh cookie), the user was redirected to `/login?error=session_expired` without any infinite loop. Network tab showed exactly 2 failed requests (original + refresh), not an infinite sequence.

---

### Example 3: `TestCase` vs `TransactionTestCase` for Threading

**AI initial suggestion**: Use `TestCase` for the concurrency test.

**Why it was wrong**: Django's `TestCase` wraps the entire test in a single database transaction for fast cleanup. When threads try to use `select_for_update()` inside nested `transaction.atomic()` calls, they create SAVEPOINT blocks inside the outer TestCase transaction. PostgreSQL cannot escalate a lock within a nested SAVEPOINT to an exclusive lock — both threads deadlock waiting for each other.

**Correction**: Changed to `TransactionTestCase`, which cleans up via `TRUNCATE` between tests. Each thread can open and commit its own real database transaction.

**Verification**: With `TestCase`, the test hung indefinitely. With `TransactionTestCase`, it completed in ~1-2 seconds with correct results. Ran 10 consecutive times to confirm no flakiness.

---

## Summary

AI was highly productive for scaffolding, boilerplate, and well-understood patterns (Docker Compose structure, DRF serializers, React routing). It required supervision and correction on:
1. **Security details** (email vs. google_id identity, email_verified check)
2. **Edge cases in async logic** (JWT refresh infinite loop)
3. **Django testing internals** (TestCase transaction isolation interacting with threads)

Every critical piece of code was reviewed against documentation, traced manually, or tested empirically before being accepted.
