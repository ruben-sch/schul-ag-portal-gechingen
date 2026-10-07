# AGENTS.md - AI Development Guide

## Project Overview
The AG-Verwaltungsportal Schlehengäuschule Gechingen is a web platform for managing, registering, and automatically allocating school extracurricular activities (AGs) using an automated fair lottery algorithm. It provides dedicated interfaces for parents, activity leaders, and school administrators, authenticated via passwordless magic links. The core stack comprises Python 3.14 (Django 6 needs 3.12+), Django 6.1+, PostgreSQL 15, Gunicorn, WhiteNoise, and Traefik, containerized with Docker Compose.

## Critical Setup & Execution Commands
- **Run commands in the dev container**, not the local `.venv` (it is Python 3.9 and cannot install Django 6; CI and the image use 3.14): `docker compose exec web python manage.py <cmd>`. Start the stack with `make up` (web, postgres, traefik, mailpit) if it isn't running.
  - The container bind-mounts the repo and runs `runserver`, so code edits live-reload. Re-run `make up` only after changing `requirements.txt` or the `Dockerfile`.
- **Database Migrations**:
  - Make migrations: `docker compose exec web python manage.py makemigrations`
  - The container applies migrations on start; manually: `docker compose exec web python manage.py migrate`
- **Testing & Quality Assurance**:
  - Unit tests: `docker compose exec web python manage.py test ags`
    - Single test: `docker compose exec web python manage.py test ags.tests.test_lottery.<Class>.<method>`
    - Tests always use in-memory sqlite (`config/settings.py` overrides the DB when `test` is in argv); outside the container they still need `SECRET_KEY` set.
  - UI simulation: `make test` runs `simulate_ui.py` against the running stack. It is NOT the unit test suite.
  - Linting: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`. Only this run fails CI; the complexity/line-length run is `--exit-zero` (advisory).
  - Security check: `bandit -r ags/`
  - flake8 and bandit are not in `requirements.txt`; install them in the container if missing. The `verify` skill (`.agents/skills/verify/`) runs all CI checks.
- **Database Utilities**:
  - Soft reset (clears test data): `make reset-soft`
  - Hard reset (rebuilds DB from scratch): `make reset-hard`
  - Semester rollover: `make next-semester` (`python manage.py next_semester`)

## Django & Python Style Rules
- **Framework Context**: Codebase is implemented in Django 6.1+ (MVT architecture with `ags/` app and `config/` project core); adhere to Django/Python architectural standards.
- **Route & View Design**: Keep request handlers modular in `ags/views.py` and register routes explicitly in `ags/urls.py`. Type-hint new or touched view signatures and response helpers (`django.http.HttpRequest`, `django.http.HttpResponse`).
- **Separation of Concerns**: Do not place business logic in views. Keep the lottery in `ags/utils.py`, other business logic in `ags/services.py`, email notifications in `ags/emails.py`, and forms in `ags/forms.py`.
- **Model Integrity**: Define business validation in model `clean()` methods (e.g., student grade constraints) and invoke `full_clean()` in `save()` (currently only `Anmeldung` does; follow that pattern for new validation).
- **Configuration Management**: Access environment variables strictly via `environ.Env` in `config/settings.py`. Never read `os.environ` directly in application logic.
- **Code Quality**: Adhere to PEP 8 with a maximum line length of 127 and max complexity of 10 as enforced by CI Flake8 checks.

## Domain
- UI text, comments, and the Makefile are German; keep new user-facing strings German. Domain terms: AG, Anmeldung, SchuelerProfile, Klassenstufe (1–4), Warteliste, Halbjahr, Leiter.
- `ArchivEintrag.halbyahr` is a misspelled field name — don't "fix" it without a migration.
- Students pick at most 5 AGs with priority 1–5 (enforced in `Anmeldung.clean()`).

## Git & Releases
- Conventional commits (`feat:`, `fix(scope):`, `chore:` …). Branches: `feat/…`, `fix/…`.
- PRs are squash-merged; the PR title becomes the commit on `main` and drives release-please (`CHANGELOG.md`, version bumps), so it must be a valid conventional-commit title.
- Push to `main` deploys to staging; a published release deploys to production.

## Agent Tooling
- Shared skills live in `.agents/skills/` and shared hook scripts in `.agents/hooks/`. Tool-specific wiring (e.g. `.claude/`) only points there; edit the files in `.agents/`.

## Safety & Security Boundaries
- **No Raw SQL**: Always query via the Django ORM (`QuerySet`). Never execute raw SQL queries via `cursor.execute()` or `extra()`.
- **Schema Migrations**: Never manually alter database tables. Always generate a Django migration file (`makemigrations`). Production runs `migrate` on container start and brief downtime is acceptable, so migrations need not stay compatible with the previous release.
- **Secrets Management**: Never commit secrets or credentials. Read `SECRET_KEY`, `POSTGRES_PASSWORD`, and SMTP keys from `.env` or CI/CD secrets.
- **Authentication & CSRF**: Protect all state-changing endpoints with CSRF tokens. Maintain `django-sesame` token TTL (`SESAME_MAX_AGE`) and do not disable security headers in production.
- **Autonomous vs. Approval Boundaries**:
  - *Autonomous*: Creating test cases, modifying view logic, adding non-destructive model fields, updating documentation.
  - *Halt & Ask*: Running destructive or production-touching targets (`make reset-hard`, `make reset-soft`, `make restore-db`, `make next-semester`, `make download-db`), dropping columns/tables, or modifying production deployment configurations.

## Reference Index
- [`manage.py`](manage.py): Django CLI execution entry point.
- [`config/settings.py`](config/settings.py): Application configuration, middleware, and security settings.
- [`config/urls.py`](config/urls.py): Root URL dispatcher routing to app endpoints.
- [`ags/models.py`](ags/models.py): Core domain models (`AG`, `SchuelerProfile`, `Anmeldung`, `ArchivEintrag`, `AppConfig`).
- [`ags/views.py`](ags/views.py): HTTP request handlers and dashboard controllers.
- [`ags/services.py`](ags/services.py): Core business logic (registration, dashboards, stats).
- [`ags/utils.py`](ags/utils.py): Two-phase lottery allocation (`run_lottery`, `reset_lottery`).
- [`ags/emails.py`](ags/emails.py): Email generation and dispatch via magic links.
- [`ags/tests/`](ags/tests): Unit and integration test suite (`test_models.py`, `test_views.py`, `test_lottery.py`, `test_emails.py`).
- [`docker-compose.yml`](docker-compose.yml) & [`Makefile`](Makefile): Local containerization and shortcut command runner.
- [`docs/adr/`](docs/adr): Architecture Decision Records (`001-bootstrap-investigation.md`, `002-staging-environment.md`).
- [`.github/workflows/test.yml`](.github/workflows/test.yml): CI linting (Flake8), security audit (Bandit), and test pipeline.
