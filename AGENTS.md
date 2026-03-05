# Style
All functions must have type annotations and docstrings
Docstrings should follow the Google style guide

# Linting
Formatters will be run on all code automatically, so do not waste time on formatting and import ordering. Just write the code and let the linters fix the formatting.

# Backend tests
Tests should have GIVE/WHEN/THEN docstrings

Run using django's test runner, e.g.:
```
cd /workspace/deep_mtg_2/app && /workspace/deep_mtg_2/.venv/bin/python manage.py test
```

# Frontend tests
Run tests using bun, e.g.:
```
cd /workspace/deep_mtg_2/frontend && bun run test --run
```

# Frontend E2E tests
These tests use Playwright. Do not try to run them youself. Ask the user to run them for you.
