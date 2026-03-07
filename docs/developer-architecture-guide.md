# Deep MTG Developer Architecture Guide

This guide is a fast, high-level map of the project for new contributors.
It focuses on **where code lives**, **what owns what**, and **how requests/flows move through the system**.

---

## 1) System at a glance

Deep MTG is a full-stack app for generating and managing Magic: The Gathering decks.

- **Frontend**: Next.js app (`frontend/`) for UI, Google sign-in, and user interactions.
- **Backend**: Django + Django Ninja API (`app/`) for business logic, data, auth token exchange, and deck orchestration.
- **Async workers**: Celery for long-running AI deck generation tasks.
- **Data stores**:
  - Postgres for relational app data (users, decks, cards, build tasks, refresh tokens)
  - Redis for rate limits and quota tracking
  - Qdrant for vector search over card embeddings
- **Reverse proxy**: Caddy routes `/` to frontend and `/api/*` to backend in local/dev docker flows.

---

## 2) Repository layout (what lives where)

## Root

- `README.md`: setup, production commands, and card ingestion commands
- `docker-compose*.yml`, `Dockerfile`, `Caddyfile`: containerized runtime
- `app/`: Django backend project
- `frontend/`: Next.js frontend project
- `data/done/*.json`: MTG JSON set data used for ingestion

## Backend (`app/`)

- `app/`: Django project config (`settings.py`, `urls.py`, `celery.py`)
- `appauth/`: auth routes, JWT/refresh token logic, middleware
- `appuser/`: user-account features (export/delete)
- `appcards/`: card/deck domain models + routes + ingestion commands
- `appai/`: deck-building orchestration, build status, Celery tasks
- `appsearch/`: semantic card search integration (Qdrant)
- `appcore/`: shared infra modules (redis client, decorators, shared utilities)

## Frontend (`frontend/`)

- `app/`: App Router pages + route handlers
  - `dashboard/`, `decks/`, `cards/search/`, `login/`, etc.
  - `backend-auth/*`: Next route handlers that bridge FE auth session to BE cookies
  - `api/auth/[...nextauth]/route.ts`: NextAuth endpoint
- `lib/`: auth/session/backend fetch helpers
- `components/`: shared UI components
- `proxy.ts`: route protection/redirect middleware

---

## 3) Backend architecture and responsibilities

## API entrypoint

`app/app/urls.py` creates a single `NinjaAPI` at `/api/app/` and mounts routers:

- `/api/app/ai/*` → deck generation workflows
- `/api/app/cards/*` → cards and decks
- `/api/app/search/*` → card semantic search
- `/api/app/user/*` → account operations
- `/api/app/token/*` → token exchange/refresh (no access-token auth on these routes)

`/healthz` is a plain health check endpoint.

## Core backend apps

### `appauth`

- Handles Google token exchange and refresh-token rotation.
- Issues backend JWT access tokens + refresh tokens.
- Applies auth rate limits.
- `CookieAuthCSRFMiddleware` enforces CSRF when authenticated via backend auth cookies on unsafe methods.

### `appcards`

- Owns card/deck data models:
  - `Card`, `Printing`
  - `Deck`, `DeckCard`, `DailyDeckTheme`
- Exposes routes for:
  - deck list/detail/full detail/update/delete
  - daily theme
  - card set codes and tags
- Maintains deck validity basics and card metadata mapping.

### `appai`

- Owns async deck build orchestration:
  - create deck build task records
  - enforce daily build quota
  - enforce relevance guardrails
  - enqueue Celery task (`construct_deck`)
  - expose build status polling API

### `appsearch`

- Exposes search endpoint for cards using:
  - request-level filters (set codes/colors/tags)
  - vector query to Qdrant
  - DB hydration of card IDs back into card payloads
- Enforces layered rate limits (5s, 1m, 1h windows).

### `appuser`

- User self-service endpoints:
  - account export
  - two-step account deletion (request token + confirm deletion)
- Adds export/delete rate-limiting and short-lived signed deletion token flow.

## Async and scheduling

- Celery app is initialized in `app/app/celery.py`.
- Task queues include `default` and `llm`.
- Deck construction task (`appai/tasks/construct_deck.py`) updates build state transitions (`PENDING` → `IN_PROGRESS` → `COMPLETED`/`FAILED`).
- Periodic jobs in Django settings run:
  - daily deck theme generation (interval-triggered with internal once-per-day guard)
  - cleanup of old deck-build task records

---

## 4) Frontend architecture and responsibilities

## Routing and page ownership

- `app/login`: Google sign-in UX and auth error display.
- `app/dashboard`: deck list, filters, generation status polling, navigation hub.
- `app/decks/generate`: prompt-based generation UX, quota checks, set-code selection, status polling.
- `app/decks/[deckId]`: full deck view/edit/delete/regenerate and card replacement exploration.
- `app/cards/search`: semantic card search with filters and optional source-deck context.
- `app/dashboard/account`: export account data and delete account flow.

## Session + auth model

- NextAuth (`lib/auth.ts`) manages Google OAuth and stores Google ID token in session.
- `proxy.ts` protects `/dashboard` and `/decks` routes.
- `app/providers.tsx` runs `BackendUserSync`:
  - if signed in, exchange Google token for backend tokens
  - if sync fails, clear backend cookies and force sign-out

## Backend token bridge (frontend-owned route handlers)

`frontend/app/backend-auth/*` routes are the bridge between browser session and backend API auth:

- `/backend-auth/exchange`: call backend `/api/app/token/exchange`; set cookies:
  - `backend_access_token` (httpOnly)
  - `backend_refresh_token` (httpOnly)
  - `backend_csrf_token` (readable by browser JS)
- `/backend-auth/refresh`: rotate backend tokens using refresh token cookie
- `/backend-auth/clear`: clear backend auth cookies

`lib/backend-auth.ts` centralizes API calling with:

- `backendFetch` wrapper
- CSRF header injection for unsafe methods
- 401 recovery via refresh then exchange fallback

---

## 5) Major process and data flows

## Flow A: Sign-in and backend token bootstrap

1. User signs in via Google (NextAuth).
2. Frontend session includes `googleAuthToken`.
3. `BackendUserSync` calls `/backend-auth/exchange`.
4. Route handler calls backend `/api/app/token/exchange`.
5. Backend validates Google token and issues backend access/refresh tokens.
6. Browser gets backend auth cookies and can call `/api/app/*` through `backendFetch`.

## Flow B: Deck generation (async)

For a dedicated walkthrough, see [`docs/deck-building.md`](deck-building.md).

1. User submits prompt in `decks/generate`.
2. FE POSTs `/api/app/ai/deck/` with prompt (+ optional `deck_id` and set filters).
3. BE checks:
   - daily quota
   - deck ownership (if regenerating)
   - no active pollable build already running
   - relevance guardrail
4. BE creates `DeckBuildTask` + enqueues Celery `construct_deck` task.
5. FE polls `/api/app/ai/deck/build_status/{task_id}/` every ~2.5s.
6. On `COMPLETED`, FE navigates to `/decks/{deckId}` and fetches full deck data.

## Flow C: Dashboard deck status tracking

1. FE loads deck summaries from `/api/app/cards/deck/`.
2. FE loads pollable statuses from `/api/app/ai/deck/statuses/`.
3. FE periodically checks active build statuses and refreshes deck list.

## Flow D: Card search

1. FE loads set-code/tag filters from card metadata endpoints.
2. User submits query + filters to `/api/app/search/search/`.
3. BE applies rate limits, builds DSL query, searches Qdrant, and hydrates card rows from Postgres.
4. FE renders ranked card results and relevance scores.

## Flow E: Account export and deletion

1. FE triggers export via `/api/app/user/me/export/` and downloads JSON.
2. For deletion, FE requests token via `/api/app/user/me/delete-request/`.
3. FE confirms deletion via `/api/app/user/me/` with token payload.
4. BE validates signed token + nonce, deletes user, FE clears auth and signs out.

## Flow F: Card data ingestion + enrichment (ops workflow)

In typical order:

1. `manage.py 1_add_cards --card-json-path ...`
   - parse MTGJSON
   - upsert base card records + printings
2. `manage.py 2_generate_card_summaries`
   - generate LLM summaries + tags for cards missing summary
3. `manage.py 3_embed_cards`
   - generate card embeddings
   - upsert vectors into Qdrant

---

## 6) Quick onboarding checklist for new developers

1. Read this guide, then skim backend `app/app/urls.py` and frontend `frontend/app/` routes.
2. Run app stack in docker and verify:
   - login works
   - dashboard loads
   - can start a deck generation and observe status transitions
3. Learn one vertical slice end-to-end:
   - start with `frontend/app/decks/generate/page.tsx`
   - follow API calls into `app/appai/routes/build_deck.py`
   - follow async task into `app/appai/tasks/construct_deck.py`
4. Use the ingestion commands only when refreshing card corpus/vector index.

---

## 7) Practical notes

- Most frontend API calls assume same-origin routing and cookie-based backend auth.
- Backend uses JWT access tokens + rotating refresh tokens for API auth.
- Long-running AI work is asynchronous; always think in terms of task IDs + status polling.
- Search quality and deck generation quality depend on the freshness of card summaries and embeddings.
