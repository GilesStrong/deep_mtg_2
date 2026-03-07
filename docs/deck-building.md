# Deck Building: End-to-End Guide

This document explains the dedicated deck-building flow across frontend, backend, and async workers.
It is intended for developers who want to understand how a deck gets generated, tracked, and displayed.

---

## 1) What deck building does

Deck building takes a user prompt (optionally constrained by set codes), runs async AI orchestration, and persists a generated deck plus metadata.

At a high level:

1. User submits prompt from the frontend.
2. Backend validates request (auth, quota, ownership, guardrails).
3. Backend creates a `DeckBuildTask` and enqueues Celery work.
4. Frontend polls build status until completion/failure.
5. On completion, frontend loads the full deck view.

---

## 2) Key files and ownership

## Frontend

- `frontend/app/decks/generate/page.tsx`
  - prompt input
  - set-code selection
  - quota display
  - task polling and redirect to deck page
- `frontend/app/dashboard/page.tsx`
  - list deck summaries
  - poll active generations and refresh status
- `frontend/app/decks/[deckId]/page.tsx`
  - full deck details after generation
  - regenerate flow entrypoint (reuses generate page)
- `frontend/lib/backend-auth.ts`
  - `backendFetch` wrapper for authenticated BE requests
  - refresh/retry behavior for 401s

## Backend

- `app/appai/routes/build_deck.py`
  - API endpoints for start build, check status, status metadata, and remaining quota
- `app/appai/tasks/construct_deck.py`
  - Celery task wrapper and status transitions (`IN_PROGRESS` → `COMPLETED`/`FAILED`)
- `app/appai/models/deck_build.py`
  - `DeckBuildTask` + `DeckBuildStatus`
- `app/appcards/routes/deck.py`
  - deck list/detail/full-detail/update/delete endpoints consumed before/after build
- `app/appcards/models/deck.py`
  - deck and deck-card persistence model

---

## 2.1) Graph nodes (deck construction pipeline)

The deck build runs as a `pydantic_graph` workflow in `appai/services/graphs/deck_construction.py`.

Top-level node order:

1. `BuildDeck`
2. `ValidateDeck`
3. `ClassifyCards`
4. `SetSwaps`

### `BuildDeck`

- Updates build task status to `BUILDING_DECK`.
- Runs the **main deck-constructor agent** (`run_deck_constructor_agent`).
- Increments `build_count` in graph state.
- Transitions to `ValidateDeck`.

### `ValidateDeck`

- Checks `Deck.valid` in DB.
- If invalid, loops back to `BuildDeck` (up to `MAX_BUILD_ATTEMPTS`, currently 3).
- If valid, transitions to `ClassifyCards`.

### `ClassifyCards`

- Updates build task status to `CLASSIFYING_DECK_CARDS`.
- Runs card-classifier agent to assign each deck card:
  - `role`
  - `importance`
- Transitions to `SetSwaps`.

### `SetSwaps`

- Updates build task status to `FINDING_REPLACEMENT_CARDS`.
- Selects non-critical/non-high-synergy cards for replacement pass.
- Builds search filter from:
  - allowed set codes
  - deck colors
- Runs replacement concurrently (semaphore-limited).

### Replacement subgraph (inside `SetSwaps`)

Each candidate card replacement uses `appai/services/graphs/replace_card.py`:

1. `SearchForReplacements`
   - vector search in Qdrant using current card summary
2. `FilterReplacements`
   - LLM-based replacement selection (`run_card_replacement_agent`)
3. `AddReplacements`
   - stores selected replacement options on `DeckCard.replacement_cards`

---

## 2.2) How the main agent runs (and available tools)

The main builder is `run_deck_constructor_agent` in `appai/services/agents/deck_constructor.py`.

Runtime characteristics:

- Uses model `TOOL_MODEL_THINKING`.
- Runs with `DeckBuildingDeps` context:
  - `deck_id`
  - `deck_description`
  - `available_set_codes`
  - `build_task_id`
- Receives a composed prompt containing:
  - generation request
  - current deck state (name/summary/tags if present)
  - generation history
- Has usage limits from app settings:
  - max tool/request calls per task
  - max input/output tokens
- Writes final structured output back to deck fields:
  - `name`
  - `llm_summary`
  - `short_llm_summary`
  - `tags`
  - appends prompt to `generation_history`

Tools available to the main deck-constructor agent:

- `list_deck_cards`
- `add_card_to_deck`
- `remove_card_from_deck`
- `search_for_cards`
- `inspect_card`
- `validate_deck`
- `clear_deck`

Tool behavior notes:

- `search_for_cards` applies set-code constraints and can auto-build advanced filters.
- `inspect_card` returns detailed card info (with short-lived cache).
- `validate_deck` enforces basic deck legality checks (card count and copy-count constraints).
- add/remove/clear tools mutate persisted `DeckCard` rows directly.

---

## 3) API surface used by deck building

All endpoints are under `/api/app`.

- `POST /ai/deck/`
  - starts a build
  - returns `task_id`, `deck_id`, and status URL
- `GET /ai/deck/build_status/{task_id}/`
  - returns current task status for polling
- `GET /ai/deck/statuses/`
  - returns all statuses + pollable statuses
- `GET /ai/deck/remaining_quota/`
  - returns current daily quota remaining
- `GET /cards/deck/`
  - dashboard deck summaries (with generation status)
- `GET /cards/deck/{deck_id}/full/`
  - final generated deck content (cards + summaries)

---

## 4) Runtime lifecycle

## Step A: Request submission

Frontend sends:

- prompt text
- selected set codes
- optional `deck_id` when regenerating an existing deck

Backend route (`build_deck`) checks:

- user auth + deck ownership
- no currently active build for same deck
- daily quota available
- request relevance guardrail

If no `deck_id` is provided, backend creates a new deck shell first.

## Step B: Task creation + enqueue

Backend creates a `DeckBuildTask` row (initial `PENDING`) and enqueues Celery task `construct_deck` with that task ID.

Task wrapper sets:

- `IN_PROGRESS` at start
- `COMPLETED` on success
- `FAILED` on exceptions

## Step C: Polling

Frontend polls every ~2.5 seconds via `GET /ai/deck/build_status/{task_id}/`.

- On `COMPLETED`: navigate to `/decks/{deck_id}` and fetch full deck.
- On `FAILED`: surface error and stop polling.
- On timeout or polling failure: stop polling and show recovery message.

## Step D: Post-build experience

Dashboard and deck pages consume deck APIs to show:

- latest generation status
- generated card list
- AI summaries/tags and deck metadata

---

## 5) Status model

Build statuses (from `DeckBuildStatus`) include:

- `PENDING`
- `IN_PROGRESS`
- `BUILDING_DECK`
- `CLASSIFYING_DECK_CARDS`
- `FINDING_REPLACEMENT_CARDS`
- `COMPLETED`
- `FAILED`

Clients should poll only statuses returned by `GET /ai/deck/statuses/` as `pollable`.

---

## 6) Guardrails and limits involved in deck building

- **Daily build quota** is enforced before enqueue; quota is then withdrawn.
- **Relevance guardrail** blocks non-MTG prompts.
- **Ownership checks** prevent reading/updating/deleting other users’ decks.
- **In-progress lock** prevents regenerating/deleting/editing while a build is active.

---

## 7) Debugging checklist

If deck generation appears stuck:

1. Check `/ai/deck/build_status/{task_id}/` response status progression.
2. Confirm Celery worker for `llm` queue is running.
3. Verify quota endpoint still returns expected remaining count.
4. Inspect backend logs around `construct_deck` task ID.
5. Confirm frontend polling loop was not cancelled by navigation or timeout.

If generation starts but results look poor:

1. Validate card data ingestion sequence has been run recently:
   - `1_add_cards`
   - `2_generate_card_summaries`
   - `3_embed_cards`
2. Confirm Qdrant collection exists and contains vectors.

---

## 8) Related docs

- High-level architecture guide: `docs/developer-architecture-guide.md`
- Project setup and runtime commands: `README.md`
