# AGENTS.md - AI Development Guide

## Project Overview
The AG-Verwaltungsportal Schlehengäuschule Gechingen is a web platform for managing, registering, and automatically allocating school extracurricular activities (AGs) using an automated fair lottery algorithm. It provides dedicated interfaces for parents, activity leaders, and school administrators, authenticated via passwordless magic links. The core stack comprises Python 3.11+, Django 4.2+, PostgreSQL 15, Gunicorn, WhiteNoise, and Traefik, containerized with Docker Compose.

## Critical Setup & Execution Commands
- **Virtual Environment & Dependencies**:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install --upgrade pip && pip install -r requirements.txt`
- **Database Migrations**:
  - Make migrations: `python manage.py makemigrations`
  - Apply migrations: `python manage.py migrate` (Docker: `docker compose run --rm web python manage.py migrate`)
- **Development Server**:
  - Docker (recommended): `make up` (spins up web, postgres, traefik, mailpit)
  - Local: `python manage.py runserver 0.0.0.0:8000`
- **Testing & Quality Assurance**:
  - Unit tests: `python manage.py test ags`
  - UI simulation: `make test` (executes `simulate_ui.py` inside container)
  - Linting: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
  - Security check: `bandit -r ags/`
- **Database Utilities**:
  - Soft reset (clears test data): `make reset-soft`
  - Hard reset (rebuilds DB from scratch): `make reset-hard`
  - Semester rollover: `make next-semester` (`python manage.py next_semester`)

## Django & Python Style Rules
- **Framework Context**: Codebase is implemented in Django 4.2+ (MVT architecture with `ags/` app and `config/` project core); adhere to Django/Python architectural standards.
- **Route & View Design**: Keep request handlers modular in `ags/views.py` and register routes explicitly in `ags/urls.py`. Type-hint view signatures and response helpers (`django.http.HttpRequest`, `django.http.HttpResponse`).
- **Separation of Concerns**: Do not place business logic in views. Keep allocation algorithms in `ags/services.py`, email notifications in `ags/emails.py`, and forms in `ags/forms.py`.
- **Model Integrity**: Define business validation in model `clean()` methods (e.g., student grade constraints) and ensure `full_clean()` is invoked in `save()`.
- **Configuration Management**: Access environment variables strictly via `environ.Env` in `config/settings.py`. Never read `os.environ` directly in application logic.
- **Code Quality**: Adhere to PEP 8 with a maximum line length of 127 and max complexity of 10 as enforced by CI Flake8 checks.

## Safety & Security Boundaries
- **No Raw SQL**: Always query via the Django ORM (`QuerySet`). Never execute raw SQL queries via `cursor.execute()` or `extra()`.
- **Schema Migrations**: Never manually alter database tables. Always generate a Django migration file (`python manage.py makemigrations`) and verify backward compatibility before running `migrate`.
- **Secrets Management**: Never commit secrets or credentials. Read `SECRET_KEY`, `POSTGRES_PASSWORD`, and SMTP keys from `.env` or CI/CD secrets.
- **Authentication & CSRF**: Protect all state-changing endpoints with CSRF tokens. Maintain `django-sesame` token TTL (`SESAME_MAX_AGE`) and do not disable security headers in production.
- **Autonomous vs. Approval Boundaries**:
  - *Autonomous*: Creating test cases, modifying view logic, adding non-destructive model fields, updating documentation.
  - *Halt & Ask*: Running destructive database resets (`make reset-hard`, `make restore-db`), dropping columns/tables, or modifying production deployment configurations.

## Reference Index
- [`manage.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/manage.py): Django CLI execution entry point.
- [`config/settings.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/config/settings.py): Application configuration, middleware, and security settings.
- [`config/urls.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/config/urls.py): Root URL dispatcher routing to app endpoints.
- [`ags/models.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/ags/models.py): Core domain models (`AG`, `SchuelerProfile`, `Anmeldung`, `ArchivEintrag`, `AppConfig`).
- [`ags/views.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/ags/views.py): HTTP request handlers and dashboard controllers.
- [`ags/services.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/ags/services.py): Two-phase lottery allocation algorithm and core business logic.
- [`ags/emails.py`](file:///Users/ruben/projects/schul-ag-portal-gechingen/ags/emails.py): Email generation and dispatch via magic links.
- [`ags/tests/`](file:///Users/ruben/projects/schul-ag-portal-gechingen/ags/tests): Unit and integration test suite (`test_models.py`, `test_views.py`, `test_lottery.py`, `test_emails.py`).
- [`docker-compose.yml`](file:///Users/ruben/projects/schul-ag-portal-gechingen/docker-compose.yml) & [`Makefile`](file:///Users/ruben/projects/schul-ag-portal-gechingen/Makefile): Local containerization and shortcut command runner.
- [`docs/adr/`](file:///Users/ruben/projects/schul-ag-portal-gechingen/docs/adr): Architecture Decision Records (`001-bootstrap-investigation.md`, `002-staging-environment.md`).
- [`.github/workflows/test.yml`](file:///Users/ruben/projects/schul-ag-portal-gechingen/.github/workflows/test.yml): CI linting (Flake8), security audit (Bandit), and test pipeline.
