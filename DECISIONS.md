# Architecture Decisions

This document records non-trivial engineering decisions made during the implementation of the Sessions Marketplace. Each decision includes the problem, options considered, the choice made, reasoning, trade-offs, and consequences.

---

## Decision 1: JWT Storage — HttpOnly Cookies vs. localStorage

### Problem / Ambiguity

JWTs need to be stored somewhere on the client. The two main options have fundamentally different security profiles.

### Options Considered

**Option A: localStorage**
- Store access token in `localStorage`, send via `Authorization: Bearer` header.
- Simple to implement, works with standard DRF `TokenAuthentication`.
- **Risk**: JavaScript can read `localStorage`. Any XSS vulnerability in the application (or any included library) can steal the token and make authenticated requests on behalf of the user until it expires.

**Option B: HttpOnly Cookies**
- Store tokens in `HttpOnly` cookies, which browsers send automatically and JavaScript cannot read.
- Requires custom DRF authentication class to read from cookies.
- **Risk**: Susceptible to CSRF if misconfigured. However, the browser's `SameSite` cookie attribute provides strong CSRF protection without requiring CSRF tokens on pure API requests.
- Requires `withCredentials: true` on Axios.

**Option C: In-memory (React state)**
- Store token only in React state — lost on page refresh.
- Effectively forces re-login on every page load. Not acceptable for a marketplace.

### Choice

**Option B: HttpOnly Cookies** with `SameSite=Lax` in development.

### Reasoning

XSS is significantly more common than CSRF in modern web applications, and XSS is completely mitigated by HttpOnly cookies. The SameSite attribute provides effective CSRF protection for same-site form submissions. Since Nginx proxies everything through the same origin, there are no cross-origin requests, making CSRF even less relevant.

### Trade-off

- Cannot use standard `Authorization: Bearer` header pattern.
- More complex Nginx configuration required (cookie passthrough headers).
- Custom DRF authentication class required.
- Requires `withCredentials: true` everywhere — small risk if CORS is misconfigured.

### Consequence

The frontend cannot read or manipulate tokens. A compromised XSS payload cannot steal authentication. Session state is determined entirely by the backend `/api/auth/me/` call, which is the source of truth.

---

## Decision 2: Booking Capacity Enforcement — `select_for_update()` Row Locking

### Problem / Ambiguity

Session bookings must never exceed `capacity`. The naive implementation is:

```python
count = Booking.objects.filter(session=session, status='active').count()
if count < session.capacity:
    Booking.objects.create(...)  # RACE CONDITION HERE
```

With multiple Gunicorn workers, two requests can both read `count = 0`, both conclude `0 < 1`, and both INSERT — creating two bookings for a capacity-1 session.

### Options Considered

**Option A: Application-level lock (process-local mutex)**
- Use Python's `threading.Lock` to serialize booking attempts.
- **Fatal flaw**: Only works within a single process. With multiple Gunicorn workers (we use 4), each process has its own lock. Cross-process race conditions remain.

**Option B: Redis distributed lock**
- Use Redis `SETNX` or `redlock` to serialize across processes.
- Correct if implemented properly.
- **Cost**: Adds Redis as a required infrastructure dependency. More complexity, more failure modes, more operational overhead. Overkill for a marketplace with PostgreSQL already present.

**Option C: PostgreSQL `select_for_update()` inside `transaction.atomic()`**
- Acquire a row-level exclusive lock on the session row.
- All concurrent transactions block at the lock until the first commits.
- Standard pattern for reservation systems.
- **Correct across processes**: The lock is held in the database, not application memory.

### Choice

**Option C: `select_for_update()` inside `transaction.atomic()`**

```python
with transaction.atomic():
    session = Session.objects.select_for_update().get(pk=session_id)
    active_count = Booking.objects.filter(session=session, status='active').count()
    if active_count >= session.capacity:
        raise SessionFullError(...)
    Booking.objects.create(...)
```

### Reasoning

PostgreSQL is already the required database. Its row-level locking is ACID-compliant, cross-process, and requires no additional infrastructure. The pattern is well-understood and widely used in reservation systems (airline seats, event tickets, etc.).

### Trade-off

- Serializes all concurrent booking attempts for the **same session**. Under very high concurrency for a single session, this creates a queue at the database.
- For a marketplace with many sessions, this is acceptable — each session's bookings are independent.
- At extreme scale, an optimistic concurrency control approach with retry loops might reduce lock contention, but this is premature optimization.

### Consequence

The capacity invariant holds even with N Gunicorn workers making simultaneous requests. The concurrency test (`test_concurrency.py`) demonstrates this empirically with threading.Barrier-synchronized requests.

---

## Decision 3: Duplicate Booking Prevention — Partial Unique Index

### Problem / Ambiguity

A user should not be able to have two active bookings for the same session. But a user should be able to cancel a booking and rebook later.

### Options Considered

**Option A: Application-level check only**
```python
if Booking.objects.filter(user=user, session=session, status='active').exists():
    raise AlreadyBookedError(...)
```
**Fatal flaw**: Two concurrent identical requests from the same user can both pass this check before either commits. The database has no protection.

**Option B: `unique_together` on `(user, session)`**
- Database-level uniqueness.
- **Problem**: Prevents rebooking after cancellation. A user who cancels a booking can never rebook that session. Unacceptable UX.

**Option C: Partial unique index on `(user, session) WHERE status = 'active'`**
```sql
CREATE UNIQUE INDEX unique_active_booking_per_user_session
ON bookings_booking (user_id, session_id)
WHERE status = 'active';
```
- Database-level uniqueness only for active bookings.
- Cancelled bookings are excluded from the constraint.
- If both the application check AND the database constraint fire, the database wins — the second INSERT receives an `IntegrityError`, which we catch and convert to a meaningful error.

### Choice

**Option C: Partial unique index** via Django's `UniqueConstraint` with `condition=Q(status='active')`.

### Reasoning

The partial unique index is the only option that satisfies all requirements:
1. Prevents duplicate active bookings (at the DB level, not just application level)
2. Allows rebooking after cancellation
3. Works correctly under concurrent requests

### Trade-off

- Slightly more complex migration (partial constraint instead of simple unique_together).
- `IntegrityError` handling must be present in the booking service.

### Consequence

Even if a concurrent race bypasses the application-level check, the database INSERT will fail for the second booking. Combined with `select_for_update()`, there are two independent layers of protection.

---

## Decision 4: Session Deletion with Active Bookings

### Problem / Ambiguity

When a creator deletes a session, what happens to existing active bookings?

### Options Considered

**Option A: Cascade delete**
- Delete the session → all bookings are cascade-deleted by the database.
- Users lose their booking history. This is destructive and misleading.
- A user checking their dashboard would see the booking disappear without explanation.

**Option B: Prevent deletion if bookings exist**
- Return 409 Conflict if any active bookings exist.
- This blocks the creator from deleting a session they created.
- Poor creator UX — creators should be able to manage their sessions freely.

**Option C: Cancel active bookings, then delete session**
- All active bookings are transitioned to `status='cancelled'` before the session is deleted.
- Booking records remain; users retain their history.
- The booking shows as "Cancelled" rather than mysteriously disappearing.

### Choice

**Option C: Cancel bookings, then delete session.**

```python
session.bookings.filter(status='active').update(status='cancelled')
session.delete()
```

### Reasoning

Data integrity and user trust are paramount. Users who booked a session deserve to see that it was cancelled, not have their booking silently erased. This is consistent with how real ticketing platforms behave (Eventbrite cancels attendee tickets when an event is deleted).

### Trade-off

- Requires application logic in the delete view (not just a database cascade).
- In a production system, we would also send email notifications to affected users. This is documented in README as a known limitation.

### Consequence

Users see cancelled bookings in their history with an accurate status. No data is silently destroyed. The booking count in a creator's dashboard accurately reflects the final state.

---

## Decision 5: Timezone Strategy — UTC Throughout

### Problem / Ambiguity

Datetime storage and comparison have to be consistent. Two clocks must agree on "has this session started?": the backend's authorization check and the database query.

### Options Considered

**Option A: Store local times, convert at boundary**
- Store datetimes in creator's timezone.
- **Problem**: Which timezone is the creator's? What if they move? Comparison logic becomes complex and error-prone.

**Option B: UTC storage, display in user's timezone**
- Store all datetimes as UTC in PostgreSQL (`TIMESTAMPTZ`).
- Use `timezone.now()` (UTC) for server-side comparisons.
- Convert to local time only in the frontend for display purposes.

**Option C: User-configurable timezone preference**
- Allow users to set their timezone.
- Stored in user profile; all datetimes converted for display.
- **Out of scope**: significant additional complexity for a compact marketplace.

### Choice

**Option B: UTC storage, browser-local display.**

Django's `USE_TZ = True` and `TIME_ZONE = 'UTC'` settings enforce UTC storage. All `DateTimeField` values are timezone-aware. The frontend uses `toLocaleString()` which automatically converts to the browser's timezone.

### Reasoning

UTC is the single canonical timezone that eliminates ambiguity. Server-side comparisons (`timezone.now() >= session.start_time`) are always accurate regardless of where the server or user is located. No DST bugs.

### Trade-off

- Creators create sessions in UTC by default. The frontend's datetime-local input captures local time, which JavaScript converts to UTC before sending to the API. Potential confusion for creators who don't realize this.
- A timezone-aware session form with explicit timezone selection would improve creator UX.

### Consequence

The backend's "has this session started?" check is always correct. Two simultaneous requests from different timezones get the same authoritative answer.

---

## Decision 6: Nginx Routing — Single Entry Point, CORS Elimination

### Problem / Ambiguity

The frontend (React) needs to call the backend API. In development, they run on different ports (5173 vs 8000). This creates CORS requirements: the backend must whitelist frontend origins, and the browser adds preflight OPTIONS requests.

### Options Considered

**Option A: Direct frontend-to-backend with CORS**
- Configure `django-cors-headers` with `CORS_ALLOWED_ORIGINS = ['http://localhost:5173']`.
- Works, but:
  - CORS configuration must be kept in sync with all deployment environments.
  - Preflight requests add latency.
  - CORS misconfiguration is a common source of bugs and security issues.

**Option B: Nginx reverse proxy, same origin**
- Nginx listens on port 80.
- `/api/*` → backend:8000
- `/*` → frontend:5173
- Browser makes all requests to `http://localhost` — same origin.
- CORS is irrelevant: the browser never makes a cross-origin request.

### Choice

**Option B: Nginx reverse proxy.**

### Reasoning

Eliminating CORS eliminates an entire class of configuration bugs. The frontend code never has to know the backend's address — it always calls `/api/`. This also matches the production deployment architecture (where Nginx would serve the compiled frontend static files directly).

### Trade-off

- Adds Nginx as a required service. More containers to manage.
- HMR (Vite hot module reload) requires WebSocket proxying — handled by Nginx `proxy_set_header Upgrade $http_upgrade` config.

### Consequence

The application has a single documented entry point: `http://localhost`. No CORS headers in the backend, no cross-origin cookies issues, no preflight overhead.

---

## Booking Correctness Explanation

### Which invariants are protected by the database?

1. **Invariant A — No duplicate active bookings:**
   PostgreSQL partial unique index: `UNIQUE (user_id, session_id) WHERE status = 'active'`.
   This fires at the INSERT level — no application race can bypass it.

2. **Relational integrity:**
   Foreign key constraints ensure bookings always reference valid sessions and users.
   No orphaned bookings can exist.

3. **Capacity enforcement through locking:**
   `select_for_update()` serializes concurrent transactions at the database level.
   The active booking count read within the transaction is accurate and exclusive.

### Which invariants are protected by application logic?

1. **Invariant C — Session has not started:**
   `timezone.now() >= session.start_time` is checked in the booking service using server time.
   The database cannot enforce this automatically with a simple constraint because it depends on the current moment.

2. **Role permissions:**
   Creator-only endpoints check `user.is_creator` at the view level, backed by the `IsCreator` permission class.

3. **Session ownership:**
   Creator A cannot modify Creator B's sessions — checked with `session.creator == request.user`.

4. **Input validation:**
   DRF serializers validate capacity, start/end time relationships, and required fields before any database writes.

### Why is `remainingSeats` in the frontend insufficient?

The frontend displays `remaining_seats = 1` to two users simultaneously. Both users see capacity available. Both click "Book".

From the browser's perspective:
1. User A: sees remaining = 1, clicks Book, sends `POST /book`
2. User B: sees remaining = 1, clicks Book, sends `POST /book`

These two requests arrive at the backend nanoseconds apart. Both HTTP requests hit separate Gunicorn worker processes. Without database-level synchronization, both processes read `active_count = 0`, both conclude `0 < 1 = capacity`, both INSERT a booking.

Result without locking: 2 bookings, 0 remaining seats, capacity exceeded.

The frontend is an **untrusted concurrent client**. It can be:
- Running stale data (the page was loaded before someone else booked)
- Running on a hacked client that ignores UI checks entirely
- Running simultaneously with itself in multiple browser windows

Only the backend database, with proper transaction isolation, can guarantee the invariant.

`select_for_update()` makes this sequence atomic from the database's perspective: the second transaction cannot read the session row until the first has committed its INSERT. At that point, it reads `active_count = 1 >= capacity = 1` and correctly rejects the booking.
