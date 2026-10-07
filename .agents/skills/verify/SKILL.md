---
name: verify
description: Run the same checks CI runs (gating flake8, bandit, Django unit tests) inside the dev container. Use after making code changes and before committing or opening a PR.
---

Run the CI checks from `.github/workflows/test.yml` inside the `web` container.

1. Make sure the stack is up: `docker compose ps --status running web`. If `web` is not running, run `make up` and wait until `docker compose exec web python manage.py check` succeeds.
2. Make sure the tools exist (they are not in `requirements.txt`):
   `docker compose exec web sh -c 'command -v flake8 >/dev/null && command -v bandit >/dev/null || pip install -q flake8 bandit'`
3. Run each check and keep going even if one fails, so you can report all three:
   - Lint (gates CI): `docker compose exec web flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
   - Security: `docker compose exec web bandit -q -r ags/`
   - Tests: `docker compose exec web python manage.py test ags`
4. Optionally run the advisory lint and mention new findings only in files you changed:
   `docker compose exec web flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics`

Report a short pass/fail line per check. For failures, quote the relevant output and fix them if they come from the current change. Do not run `make test` (UI simulation) or any `reset-*`, `restore-db`, or `next-semester` target as part of verification.
