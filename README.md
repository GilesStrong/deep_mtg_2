# Deep MTG 2

AI-powered Magic: The Gathering deck builder.

## Developer Docs

- High-level backend/frontend architecture and flows: [`docs/developer-architecture-guide.md`](docs/developer-architecture-guide.md)
- Dedicated deck-building flow guide: [`docs/deck-building.md`](docs/deck-building.md)

## Fresh Clone Setup (Docker)

These steps assume the repo has just been cloned and you want to run the app locally with Docker.

### Dev Container (recommended in VS Code)

This repo includes a `.devcontainer` config.

1. Open the repo in VS Code.
2. Run **Dev Containers: Reopen in Container**.
3. Wait for the container to finish building.
4. Continue with the setup steps below from inside the devcontainer terminal.

Using the devcontainer gives you a consistent toolchain and avoids host dependency drift.

### 1) Prerequisites

- Docker + Docker Compose
- Google OAuth credentials (for login)
- An LLM service reachable on the external Docker network `llm_net` (required for deck generation)

### 2) Create env files

Backend env (repo root):

```bash
cp .env.tests .env
```

Frontend env:

```bash
cp frontend/.env.example frontend/.env
```

Then edit values as needed:

- In `.env`: backend/auth/API keys and Django/JWT settings
- In `frontend/.env`: Google OAuth + NextAuth settings (`NEXTAUTH_URL` should be `http://localhost:3000` for local)

### 2.1) Configure `AUTH_RATE_LIMIT_TRUSTED_PROXY_CIDRS`

`AUTH_RATE_LIMIT_TRUSTED_PROXY_CIDRS` controls which proxy IP ranges are trusted to provide forwarded client IP headers (such as `X-Forwarded-For` and `CF-Connecting-IP`) for auth rate limiting.

Use this rule:

- Include only proxy ranges that connect directly to Django (typically Caddy on the internal Docker network).
- Do **not** include broad/public ranges like `0.0.0.0/0`.

Examples:

- Single trusted proxy IP: `AUTH_RATE_LIMIT_TRUSTED_PROXY_CIDRS=["172.30.5.10/32"]`
- Trusted Docker subnet: `AUTH_RATE_LIMIT_TRUSTED_PROXY_CIDRS=["172.30.5.0/24"]`

How to discover values:

```bash
# Inspect subnet used by your compose network
docker network inspect deepmtg_network_prod --format '{{(index .IPAM.Config 0).Subnet}}'

# Inspect proxy container IP on that network
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' deepmtg_2_prod-proxy-1
```

For local dev where direct spoofing risk is lower, you can keep this as an empty list (`[]`), but for staging/production set it explicitly.

### 2.2) Configure `ADMIN_ALLOWLIST_CIDRS`

`ADMIN_ALLOWLIST_CIDRS` controls which source CIDRs can access `/admin/*` through Caddy.

Format: space-separated CIDR list (not JSON).

Use this rule:

- Include only trusted operator/VPN/internal CIDRs.
- Do **not** use broad ranges like `0.0.0.0/0`.

Examples:

- Single office egress IP: `ADMIN_ALLOWLIST_CIDRS=198.51.100.44/32`
- Multiple ranges: `ADMIN_ALLOWLIST_CIDRS=198.51.100.44/32 10.42.0.0/16`

If no explicit value is provided in compose, the default is `127.0.0.1/32` (effectively closed to public traffic).

Quick start defaults:

- `cp .env.tests .env` gives you a backend baseline suitable for local/dev bootstrap.
- `cp frontend/.env.example frontend/.env` gives you the frontend baseline.
- You still need to fill real OAuth/API secrets before full auth + deck generation workflows will work.

### 3) Create required external Docker network

`docker-compose.yml` expects an external network named `llm_net`.

```bash
docker network create llm_net
```

### 4) Set up Ollama on `llm_net`

Card embedding and search depends on an LLM endpoint. This project defaults to:

- `OLLAMA_BASE_URL=http://ollama:11434`

If you run Ollama in a separate compose project, attach it to `llm_net` using a service like:

```yaml
services:
	ollama:
		image: ollama/ollama:latest
		container_name: ollama
		restart: unless-stopped
		volumes:
			- ~/infra/ollama:/root/.ollama
		networks:
			- llm_net
			- 127.0.0.1:11434:11434
		deploy:
			resources:
				reservations:
					devices:
						- driver: nvidia
							count: all
							capabilities: [gpu]

networks:
	llm_net:
		name: llm_net
```

After starting Ollama, pull the models referenced by your `.env` (`EMBEDDING_MODEL`), for example:

```bash
docker exec -it ollama ollama pull snowflake-arctic-embed2
```

Optional host check:

```bash
curl http://127.0.0.1:11434/api/tags
```

### 5) Build and start services

```bash
docker compose up -d --build
```

### 6) Run database migrations

```bash
docker compose exec web python app/manage.py migrate
```

### 7) Open the app

- App URL: http://localhost:3000
- Backend health: http://localhost:3000/healthz

### 8) Useful dev commands

Stop services:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f web
docker compose logs -f frontend
docker compose logs -f celery_llm_worker
```

Run backend tests:

```bash
docker compose exec web python app/manage.py test
```

Run frontend tests:

```bash
docker compose exec frontend bun run test --run
```

## Production Server Commands

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

## Card Data Pipeline (Load New Expansion)

Use MTGJSON set files from https://mtgjson.com/downloads/all-sets/.

Run inside the backend container:

1) Load cards into Postgres:
```bash
docker compose exec web python app/manage.py 1_add_cards --card-json-path /path/to/cards.json
```

2) Generate summaries and tags:
```bash
docker compose exec web python app/manage.py 2_generate_card_summaries
```

3) Generate embeddings and upsert to Qdrant:
```bash
docker compose exec web python app/manage.py 3_embed_cards
```

Note: Deck generation and semantic search quality depend on this pipeline being populated.
