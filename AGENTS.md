# Style
All functions must have type annotations and docstrings
Docstrings should follow the Google style guide

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
