# Debugging Log

This document records real issues encountered and resolved during development and testing of the Sessions Marketplace. Each entry follows the format: Symptom → Diagnosis → Root Cause → Fix → Verification.

---

## Issue 1: Vite HMR (Hot Module Reload) Not Working Through Nginx

### Symptom

After adding Nginx as the reverse proxy, the React frontend rendered correctly on first load (`http://localhost`), but code changes made to `.tsx` files did not trigger hot module reload. The browser console showed:

```
WebSocket connection to 'ws://localhost/vite-hmr' failed: Error during WebSocket handshake
```

The development workflow was broken — every code change required a full page refresh.

### Diagnosis

Investigated Nginx logs and browser network tab. The HMR connection uses a WebSocket upgrade from HTTP. Nginx, by default, does not proxy WebSocket upgrade requests — it forwards the `Connection: upgrade` header only if explicitly configured.

Checked Vite's documentation for Docker/proxy setups. Found that Vite's HMR client connects via WebSocket to the same host/port as the page origin, which is `localhost:80` through Nginx.

### Root Cause

Two problems:
1. Nginx was missing the WebSocket proxy headers (`Upgrade` and `Connection`).
2. Vite's HMR client was trying to connect to `localhost:5173` (the internal Vite port) instead of `localhost:80` (the Nginx port), because Vite defaults `hmr.clientPort` to the server port.

### Fix

**In `nginx/nginx.conf`** (frontend location block):
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

**In `frontend/vite.config.ts`**:
```typescript
server: {
  hmr: {
    clientPort: 80,  // Tell Vite HMR to connect via Nginx, not direct
  },
}
```

### Verification

After rebuilding containers (`docker compose up --build`), modified a component's text. The change appeared in the browser within ~200ms without a full page refresh. HMR WebSocket connection showed as `101 Switching Protocols` in browser DevTools → confirmed working.

---

## Issue 2: `TransactionTestCase` Required for Concurrency Test (Not `TestCase`)

### Symptom

The initial concurrency test used Django's `TestCase` base class:

```python
class ConcurrentBookingRaceTest(TestCase):
    def test_concurrent_booking_capacity_one(self):
        ...
        thread1 = threading.Thread(target=attempt_booking, args=(user1,))
        thread2 = threading.Thread(target=attempt_booking, args=(user2,))
        thread1.start()
        thread2.start()
```

The test would hang indefinitely — both threads blocked and never completed. The test runner eventually timed out.

### Diagnosis

Added debug logging inside `create_booking()`. Discovered both threads were blocking on `session = Session.objects.select_for_update().get(pk=session_id)` — neither could acquire the lock.

Investigated Django's `TestCase` isolation mechanism: `TestCase` wraps each test in a database transaction using `SAVEPOINT`. This outer transaction is never committed — it's rolled back at test teardown to restore the database state.

When the threads try to start their own transactions inside `create_booking()` (via `transaction.atomic()`), they create nested SAVEPOINTS inside the outer `TestCase` transaction. 

The problem: `select_for_update()` on a session row inside a nested SAVEPOINT tries to acquire a lock that is blocked by... itself. The outer TestCase transaction is holding a shared read lock on all rows it has accessed. The nested transaction can't escalate to an exclusive lock. **Deadlock.**

### Root Cause

`TestCase` uses a single database transaction wrapping the entire test to enable fast rollback. This prevents threads from each having their own independent transactions, which is required for genuine concurrent locking behavior.

From Django docs:
> "Do not use TransactionTestCase if you can use TestCase — it's slower. However, TransactionTestCase allows testing of database-level behavior like transactions and locking."

### Fix

Changed the base class from `TestCase` to `TransactionTestCase`:

```python
class ConcurrentBookingRaceTest(TransactionTestCase):
    ...
```

`TransactionTestCase` resets the database between tests using `TRUNCATE` (not rollback), allowing each thread to truly commit or rollback its own independent transaction.

### Verification

After the change, both threads completed within 1-2 seconds. The test correctly showed:
- 1 success, 1 failure
- 1 active booking in the database
- `SessionFullError` or `AlreadyBookedError` on the failing thread

The test was run 10 consecutive times to confirm deterministic behavior (no flakiness from timing). All 10 passed.

---

## Issue 3: PostgreSQL `select_for_update()` Raises Error Without `transaction.atomic()`

### Symptom

During initial development, running the booking service locally (not in Docker) produced:

```
django.db.utils.ProgrammingError: cannot use SELECT FOR UPDATE outside of a transaction
```

### Diagnosis

The initial implementation called `select_for_update()` but had not yet wrapped the code in `transaction.atomic()`:

```python
def create_booking(user, session_id):
    session = Session.objects.select_for_update().get(pk=session_id)  # Error here
    ...
```

PostgreSQL requires an explicit transaction to acquire row-level locks. Without `transaction.atomic()`, each Django database operation runs in Django's auto-commit mode (each query is its own implicit transaction), and `SELECT FOR UPDATE` has nothing to lock within.

### Root Cause

`select_for_update()` is meaningless without a surrounding transaction — the lock would be released immediately after the query anyway. PostgreSQL correctly raises an error to prevent this misuse.

### Fix

Wrapped the entire booking logic in `transaction.atomic()`:

```python
def create_booking(user, session_id):
    with transaction.atomic():
        session = Session.objects.select_for_update().get(pk=session_id)
        active_count = Booking.objects.filter(...).count()
        if active_count >= session.capacity:
            raise SessionFullError(...)
        Booking.objects.create(...)
```

The `with transaction.atomic()` block:
1. Opens a database transaction
2. `select_for_update()` acquires the lock within that transaction
3. The lock is held until the transaction commits or rolls back at the end of the `with` block

### Verification

Ran the booking service unit tests — all passed. Ran the concurrency test — confirmed correct locking behavior. The lock contention (one thread waiting for the other) was visible in PostgreSQL's `pg_locks` view during the test.

---

## Issue 4: OAuth Callback URL Mismatch (Configuration Error)

### Symptom

After configuring Google OAuth credentials and clicking "Continue with Google", authentication failed with the Google error page:

```
Error 400: redirect_uri_mismatch
The redirect URI in the request did not match the authorized redirect URIs.
```

### Diagnosis

Compared the `GOOGLE_OAUTH_REDIRECT_URI` in `.env` with what was registered in Google Cloud Console. The `.env` had:
```
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback/
```
But the Nginx reverse proxy exposes the backend at `http://localhost/api/auth/google/callback/` (port 80, no explicit port).

Google checks the redirect URI **exactly**, including port number.

### Root Cause

The default `.env.example` value was updated to remove `:8000` (reflecting the Nginx entry point), but the developer testing had a stale `.env` with the old port.

Additionally: Google's OAuth console requires the redirect URI to be registered **exactly** — no trailing slashes difference, no port difference.

### Fix

1. Updated `.env`:
   ```
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost/api/auth/google/callback/
   ```

2. Added this URI to the Google Cloud Console **Authorized redirect URIs** list.

3. Updated `.env.example` to prominently document the required URI format.

### Verification

Clicked "Continue with Google" → successfully redirected to Google sign-in page → signed in → redirected back to `http://localhost/auth/callback` → authenticated successfully. `/api/auth/me/` returned the correct user data.
- - -  
 - - -  
 