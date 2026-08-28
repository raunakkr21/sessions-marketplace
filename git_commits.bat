@echo off
setlocal

cd /d "C:\Users\rauna\OneDrive\Desktop\sessions-marketplace"

echo === Configuring git user ===
git config user.email "dev@sessions-marketplace.com"
git config user.name "Sessions Marketplace Dev"

echo === Commit 1: Scaffold ===
git add .gitignore .env.example docker-compose.yml
git add nginx
git add backend/Dockerfile backend/entrypoint.sh backend/requirements.txt backend/manage.py
git add backend/config
git add backend/apps/__init__.py
git commit -m "chore: scaffold Django React Docker project with Nginx reverse proxy"
if errorlevel 1 echo Warning: Commit 1 may have had issues

echo === Commit 2: Auth ===
git add backend/apps/users
git commit -m "feat: add Google OAuth and JWT authentication"

echo === Commit 3: Sessions ===
git add backend/apps/sessions
git commit -m "feat: add session catalog and creator CRUD"

echo === Commit 4: Bookings ===
git add backend/apps/bookings
git commit -m "feat: add booking workflow with transactional capacity enforcement"

echo === Commit 5: Frontend ===
git add frontend
git commit -m "feat: add React/TypeScript frontend with all required pages"

echo === Commit 6: Tests ===
git add backend/apps/tests
git commit -m "test: add authorization and booking concurrency tests"

echo === Commit 7: Seed data ===
git add backend/apps/users/management
git commit -m "feat: add seed_demo management command and demo data"

echo === Commit 8: Migrations ===
git add backend/apps/users/migrations backend/apps/sessions/migrations backend/apps/bookings/migrations
git commit -m "chore: add database migrations including partial unique constraint for bookings"

echo === Commit 9: Documentation ===
git add README.md DECISIONS.md DEBUGGING.md PROMPT_LOG.md git_commits.ps1 git_commits.sh git_commits.bat
git commit -m "docs: add architecture decisions, debugging notes, and AI prompt log"

echo.
echo === All commits created! ===
git log --oneline

pause
