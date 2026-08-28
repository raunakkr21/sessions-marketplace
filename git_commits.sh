#!/usr/bin/env bash
# Git commit script for Sessions Marketplace
# Run from the repository root: bash git_commits.sh

set -e

echo "=== Configuring git user ==="
git config user.email "dev@sessions-marketplace.com"
git config user.name "Sessions Marketplace Dev"

echo "=== Commit 1: Scaffold ==="
git add .gitignore .env.example docker-compose.yml
git add nginx/
git add backend/Dockerfile backend/entrypoint.sh backend/requirements.txt backend/manage.py
git add backend/config/
git add backend/apps/__init__.py
git commit -m "chore: scaffold Django React Docker project with Nginx reverse proxy

- docker-compose.yml: 4 services (postgres, backend, frontend, nginx)
- Named volume postgres_data for persistence
- Nginx routing: /api/* to Django, /* to React with WS HMR support
- Backend: Python 3.12, Django 5.0, DRF, Gunicorn 4 workers
- Settings split: base.py / development.py
- wait_for_db management command for startup race safety"

echo "=== Commit 2: Auth ==="
git add backend/apps/users/
git commit -m "feat: add Google OAuth and JWT authentication

- Custom User model: UUID PK, google_id, email, role choices
- Google OAuth flow with CSRF state protection
- JWT in HttpOnly cookies (XSS-safe) with refresh token
- Custom DRF JWTCookieAuthentication class
- Token refresh interceptor in Axios (transparent retry)
- Consistent JSON error format (no stack traces)
- IsCreator and IsOwnerOrReadOnly permission classes
- /api/auth/google/, /callback/, /me/, /logout/, /token/refresh/
- User identity matched by google_id (not email — see DECISIONS.md)"

echo "=== Commit 3: Sessions ==="
git add backend/apps/sessions/
git commit -m "feat: add session catalog and creator CRUD

- Session model: UUID PK, creator FK, start/end time (UTC), capacity
- has_started property uses server time (timezone.now())
- Public GET /api/sessions/ and /api/sessions/{id}/ (no auth required)
- Creator-only: POST/PATCH/DELETE /api/creator/sessions/
- Creator ownership enforced server-side (403 for wrong creator)
- /api/creator/dashboard/ with annotated booking counts (no N+1)
- SessionWriteSerializer validates future start, end > start, capacity >= 1"

echo "=== Commit 4: Bookings ==="
git add backend/apps/bookings/
git commit -m "feat: add booking workflow with transactional capacity enforcement

- Booking model: status choices (active/cancelled)
- Partial unique constraint: UNIQUE(user,session) WHERE status='active'
- create_booking service: select_for_update() + transaction.atomic()
- Invariant A: duplicate booking prevented at DB level (UniqueConstraint)
- Invariant B: capacity enforced transactionally (select_for_update)
- Invariant C: started sessions rejected using server time (timezone.now)
- Invariant D: ownership enforced on PATCH/DELETE (creator check)
- POST /api/sessions/{id}/book/ -> 201/409 with descriptive errors
- GET /api/bookings/ returns active and past bookings"

echo "=== Commit 5: Frontend ==="
git add frontend/
git commit -m "feat: add React/TypeScript frontend with all required pages

- Vite + React 18 + TypeScript + React Router
- AuthProvider context bootstrapped from /api/auth/me/
- LoginPage: Google OAuth button, OAuth error display
- CatalogPage: session grid with seats bar, status badges
- SessionDetailPage: book button disabled when started/full/already-booked
- UserDashboardPage: active/past bookings, inline profile editor
- CreatorDashboardPage: session list with booking counts, create/edit/delete modal
- OAuthCallbackPage: refreshes auth context after backend redirect
- Axios interceptor: transparent token refresh on 401
- Dark mode design system with Inter font"

echo "=== Commit 6: Tests ==="
git add backend/apps/tests/
git commit -m "test: add authorization and booking concurrency tests

Authorization tests (test_authorization.py):
- USER -> creator endpoint -> 403 (required)
- Creator A -> Creator B session -> 403 (required)
- Unauthenticated -> protected endpoints -> 401
- Invalid JWT -> 401 with error detail
- Expired JWT -> 401 with 'expired' in message

Booking tests (test_bookings.py):
- Valid booking creates active booking
- Duplicate booking rejected (AlreadyBookedError)
- Full session rejected (SessionFullError)
- Started session rejected (SessionAlreadyStartedError)
- Nonexistent session returns 404
- Session deletion cancels active bookings

Concurrency test (test_concurrency.py):
- Uses TransactionTestCase (not TestCase — avoids deadlock)
- threading.Barrier(2) ensures genuinely simultaneous requests
- Verifies: 1 success, 1 failure, exactly 1 active booking in DB
- Also tests same-user duplicate booking race"

echo "=== Commit 7: Seed data ==="
git add backend/apps/users/management/
git commit -m "feat: add seed_demo management command and demo data

- Creates 2 creator accounts + 1 user account
- 5 sessions: upcoming, started, nearly-full, capacity-1 (race test)
- Outputs demo JWT tokens for API testing without OAuth
- Documents concurrency test session ID
- --clear flag to reset database"

echo "=== Commit 8: Migrations ==="
git add backend/apps/users/migrations/ backend/apps/sessions/migrations/ backend/apps/bookings/migrations/
git commit -m "chore: add database migrations

- users: User model with UUID PK, google_id unique, role choices
- sessions: Session model with start/end time index
- bookings: Booking model with partial unique constraint
  UNIQUE(user_id, session_id) WHERE status='active'
  This is the database-level guarantee for Invariant A (no duplicate active bookings)"

echo "=== Commit 9: Documentation ==="
git add README.md DECISIONS.md DEBUGGING.md PROMPT_LOG.md
git commit -m "docs: add architecture decisions and debugging notes

README.md:
- Complete setup guide, OAuth config, Docker run command
- Test commands, demo flow, persistence explanation
- Known limitations, improvement ideas

DECISIONS.md:
- 6 engineering decisions with options/reasoning/tradeoffs
- JWT HttpOnly cookies vs localStorage
- select_for_update() vs Redis lock vs in-memory lock
- Partial unique index for duplicate bookings
- Session deletion behavior (cancel bookings, not delete)
- UTC timezone strategy
- Nginx routing (eliminates CORS)
- Booking correctness explanation (why frontend check is insufficient)

DEBUGGING.md:
- 4 real debugging cases (Vite HMR, TransactionTestCase deadlock, 
  select_for_update without atomic, OAuth redirect URI mismatch)

PROMPT_LOG.md:
- 6 material prompts documented
- 3 real AI mistakes corrected (email vs google_id, retry loop, TestCase)"

echo ""
echo "=== All commits created! ==="
git log --oneline
