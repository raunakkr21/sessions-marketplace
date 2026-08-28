# Git commit script for Sessions Marketplace (PowerShell version)
# Run from the repository root: .\git_commits.ps1

$ErrorActionPreference = "Stop"
$RepoPath = "C:\Users\rauna\OneDrive\Desktop\sessions-marketplace"
Set-Location $RepoPath

Write-Host "=== Configuring git user ===" -ForegroundColor Cyan
git config user.email "dev@sessions-marketplace.com"
git config user.name "Sessions Marketplace Dev"

Write-Host "=== Commit 1: Scaffold ===" -ForegroundColor Cyan
git add .gitignore .env.example docker-compose.yml
git add nginx
git add backend/Dockerfile backend/entrypoint.sh backend/requirements.txt backend/manage.py
git add backend/config
git add "backend/apps/__init__.py"
git commit -m "chore: scaffold Django React Docker project with Nginx reverse proxy"

Write-Host "=== Commit 2: Auth ===" -ForegroundColor Cyan
git add backend/apps/users
git commit -m "feat: add Google OAuth and JWT authentication"

Write-Host "=== Commit 3: Sessions ===" -ForegroundColor Cyan
git add backend/apps/sessions
git commit -m "feat: add session catalog and creator CRUD"

Write-Host "=== Commit 4: Bookings ===" -ForegroundColor Cyan
git add backend/apps/bookings
git commit -m "feat: add booking workflow with transactional capacity enforcement"

Write-Host "=== Commit 5: Frontend ===" -ForegroundColor Cyan
git add frontend
git commit -m "feat: add React/TypeScript frontend with all required pages"

Write-Host "=== Commit 6: Tests ===" -ForegroundColor Cyan
git add backend/apps/tests
git commit -m "test: add authorization and booking concurrency tests"

Write-Host "=== Commit 7: Seed data ===" -ForegroundColor Cyan
git add backend/apps/users/management
git commit -m "feat: add seed_demo management command and demo data"

Write-Host "=== Commit 8: Migrations ===" -ForegroundColor Cyan
git add backend/apps/users/migrations backend/apps/sessions/migrations backend/apps/bookings/migrations
git commit -m "chore: add database migrations including partial unique constraint for bookings"

Write-Host "=== Commit 9: Documentation ===" -ForegroundColor Cyan
git add README.md DECISIONS.md DEBUGGING.md PROMPT_LOG.md
git commit -m "docs: add architecture decisions, debugging notes, and AI prompt log"

Write-Host ""
Write-Host "=== All commits created! ===" -ForegroundColor Green
git log --oneline
