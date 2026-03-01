# Deep MTG 2

## Installation

For development usage, we use [`uv`](https://docs.astral.sh/uv/) to handle dependency installation.
uv can be installed via, e.g.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

and ensuring that `uv` is available in your `$PATH`

Install the dependencies:

```bash
uv lock
uv sync
uv tool install pre-commit --with pre-commit-uv --force-reinstall
uvx pre-commit install
```


## Running production server:

```bash
# start
docker compose --project-name deepmtg_2_prod --env-file .env.prod -f docker-compose.prod.yml up -d --build
# check logs
docker compose --project-name deepmtg_2_prod --env-file .env.prod -f docker-compose.prod.yml logs --tail=200 proxy
# restart
docker compose --project-name deepmtg_2_prod --env-file .env.prod -f docker-compose.prod.yml up -d --force-recreate proxy
# stop
docker compose --project-name deepmtg_2_prod --env-file .env.prod -f docker-compose.prod.yml down
```

## Product / Legal Basics

The app now includes baseline product/legal UX and APIs:

- Public legal pages in the frontend:
	- `/privacy`
	- `/terms`
	- `/support`
- Account self-service (authenticated):
	- Frontend: `/dashboard/account`
	- Export user data JSON: `GET /api/app/user/me/export/`
	- Request deletion confirmation token: `POST /api/app/user/me/delete-request/`
	- Confirm deletion + remove associated records: `DELETE /api/app/user/me/` (with `confirmation_token`)
