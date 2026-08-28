# Sessions Marketplace

A full-stack booking platform where users authenticate, browse sessions, and book them; creators create and manage sessions. Built as a time-constrained internship assignment demonstrating production-minded engineering.

---

## Architecture

```
Browser
  │
  ▼
Nginx (port 80)          ← Single public entry point
  ├── /api/*  ──────────→  Django/DRF backend (port 8000 internal)
  ├── /admin/* ─────────→  Django admin (port 8000 internal)
  └── /* ───────────────→  React/Vite frontend (port 5173 internal)
                                          │
                                          ▼
                                   PostgreSQL (port 5432 internal)
```

**Why Nginx as the entry point?**
All traffic arrives from the same origin (`http://localhost`). This eliminates CORS entirely — the browser never makes a cross-origin request. See `DECISIONS.md` for full rationale.

### Authentication Flow
```
1. User clicks "Continue with Google"
2. Browser navigates to /api/auth/google/ (backend redirect)
3. Google authenticates the user
4. Google redirects to /api/auth/google/callback/
5. Backend exchanges code for tokens, creates/retrieves user
6. Backend sets JWT access + refresh tokens in HttpOnly cookies
7. Backend redirects browser to /auth/callback (frontend)
8. Frontend OAuthCallbackPage calls /api/auth/me/ to restore user state
9. User lands on the catalog page, authenticated
```

### Booking Concurrency Strategy
The booking service uses `select_for_update()` inside `transaction.atomic()`:
- Acquires a **row-level exclusive lock** on the session row
- Serializes all concurrent booking attempts for the same session at the database level
- No two transactions can simultaneously read and write the active booking count
- A partial unique index `WHERE status = 'active'` provides a final DB-level safety net for duplicate bookings

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, React Router |
| Backend | Python 3.12, Django 5.0, Django REST Framework |
| Database | PostgreSQL 16 |
| Auth | Google OAuth 2.0 + backend-issued JWTs (HttpOnly cookies) |
| Proxy | Nginx 1.27 |
| Infrastructure | Docker Compose |

---

## Prerequisites

- **Docker Desktop** (includes Docker Compose) — [download](https://www.docker.com/products/docker-desktop/)
- **Git**
- **Google OAuth credentials** (see Setup section)

You do NOT need to install Python, Node.js, or PostgreSQL locally.

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd sessions-marketplace
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:
- `DJANGO_SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(50))"`
- `POSTGRES_PASSWORD` — any strong password
- `JWT_SECRET_KEY` — generate separately from Django secret key
- `GOOGLE_OAUTH_CLIENT_ID` — from Google Cloud Console
- `GOOGLE_OAUTH_CLIENT_SECRET` — from Google Cloud Console

Leave other values as-is for local development.

### 3. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Navigate to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Add Authorized redirect URI:
   ```
   http://localhost/api/auth/google/callback/
   ```
7. Copy the **Client ID** and **Client Secret** to your `.env`

---

## Run

```bash
docker compose up --build
```

This command:
1. Builds all 4 container images (frontend, backend, postgres, nginx)
2. Starts PostgreSQL and waits for it to be healthy
3. Runs Django database migrations automatically
4. Starts Gunicorn (4 workers) and Vite dev server
5. Starts Nginx to proxy all traffic

**Application URL: http://localhost**

---

## URLs

| URL | Description |
|-----|-------------|
| `http://localhost` | Main application |
| `http://localhost/api/sessions/` | Public sessions API |
| `http://localhost/admin/` | Django admin panel |
| `http://localhost/api/auth/google/` | Initiate OAuth |

---

## Database Persistence

PostgreSQL data is stored in a **named Docker volume** (`postgres_data`):

```yaml
# docker-compose.yml
volumes:
  postgres_data:
    driver: local
```

Data survives:
- `docker compose stop` / `docker compose start`
- `docker compose down` (containers removed, volume remains)
- Application container rebuilds

Data is destroyed only with:
```bash
docker compose down -v   # WARNING: deletes all data
```

---

## Seed / Demo Data

After the application starts, populate demo data:

```bash
docker compose exec backend python manage.py seed_demo
```

This creates:
- **2 creator accounts** (alice.creator@demo.com, bob.creator@demo.com)
- **1 user account** (jane.user@demo.com)
- **5 sessions** (upcoming, in-progress, nearly-full, capacity-1 for race testing)

**Important**: Demo accounts use synthetic Google IDs and cannot sign in via OAuth directly. Use real Google credentials to sign in, then ask an admin to change your role to `creator` via Django admin if needed.

### Promote yourself to Creator (after OAuth sign-in)

```bash
docker compose exec backend python manage.py shell -c "
from apps.users.models import User
u = User.objects.get(email='your@email.com')
u.role = 'creator'
u.save()
print('Done:', u)
"
```

---

## Tests

### Run all backend tests

```bash
docker compose exec backend python manage.py test apps.tests --verbosity=2
```

### Run authorization tests specifically

```bash
docker compose exec backend python manage.py test apps.tests.test_authorization --verbosity=2
```

### Run booking invariant tests

```bash
docker compose exec backend python manage.py test apps.tests.test_bookings --verbosity=2
```

### Run concurrency / race condition test

```bash
docker compose exec backend python manage.py test apps.tests.test_concurrency --verbosity=2
```

The concurrency test:
1. Creates a session with `capacity = 1`
2. Creates two users
3. Uses a `threading.Barrier` to make both booking attempts simultaneous
4. Verifies exactly 1 succeeds, exactly 1 fails, DB has exactly 1 active booking

**This test MUST run against PostgreSQL** — it tests real row-level locking behavior.

---

## Demo Flow (Evaluator Walkthrough)

1. Open `http://localhost`
2. Click **Continue with Google** → sign in
3. Browse the session catalog
4. Click a session → view details, remaining seats
5. Click **Book This Session** → see confirmation
6. Click **My Bookings** (top nav) → see active booking

**As a Creator** (after role assignment):
1. Sign in → redirected to Creator Dashboard
2. Click **+ New Session** → fill form → create
3. See booking count on your session card
4. Click **Edit** → modify session
5. Click **Delete** → confirm deletion (bookings cancelled)

**Concurrency demo**:
1. Run seed: `docker compose exec backend python manage.py seed_demo`
2. Note the "1-on-1 Code Review Session" (capacity = 1)
3. Open two browser windows
4. Sign in as two different Google accounts
5. Both navigate to that session
6. Both click Book simultaneously
7. One succeeds, one gets "This session is fully booked"

---

## Architecture Decisions

See [`DECISIONS.md`](./DECISIONS.md) for detailed engineering decisions.

---

## Known Limitations

1. **OAuth only**: No email/password auth. Users must have a Google account.
2. **No token revocation**: JWTs cannot be invalidated before expiry (no blocklist). A compromised token is valid until it expires (60 minutes).
3. **Role assignment is manual**: New users default to `user`. Becoming a creator requires admin action. A "Request Creator Status" flow would improve UX.
4. **No email notifications**: Bookings and session changes are not emailed to users.
5. **Dev server in Docker**: The frontend uses Vite dev server (not a production build). Hot module reload works through Nginx but is not appropriate for production.
6. **No pagination**: The session catalog loads all sessions at once. Would need cursor-based pagination at scale.
7. **No cancellation UI**: Users cannot cancel bookings from the frontend (only creators can effectively cancel by deleting sessions). Cancellation endpoint would be straightforward to add.

---

## What I Would Improve With Another Day

1. **Token revocation blocklist** (Redis) — invalidate refresh tokens on logout
2. **User-initiated booking cancellation** — endpoint and UI
3. **Production Vite build** — serve static files from Nginx, not dev server
4. **Email notifications** (Celery + SMTP) — booking confirmations, session changes
5. **Pagination** — cursor-based for session list
6. **Search and filtering** — by date, creator, availability
7. **WebSockets** — real-time seat availability updates (remaining_seats)
8. **HTTPS configuration** — Let's Encrypt via certbot in Nginx
9. **CI/CD pipeline** — GitHub Actions running tests on PR
10. **OpenAPI documentation** — auto-generate from DRF using drf-spectacular
