# AI Memory System Guide

This guide explains the long-term memory system used by deck-construction agents.
It covers where memory data lives, how it is written/retrieved, and how automated maintenance works.

---

## 1) Why this exists

Deck-building agents can discover useful insights during generation (synergies, archetype patterns, replacement heuristics).
The memory system lets agents carry those insights into future generations, instead of relearning them every run.

Key design goals:

- Preserve cross-task, MTG-relevant knowledge.
- Keep memory retrieval semantic (vector search) instead of exact string matching.
- Avoid user-specific or private preference storage.
- Periodically consolidate stale/duplicate memory entries.

---

## 2) Core components

## Storage model

- Postgres model: `app/appai/models/memory.py`
  - `Memory` (`id`, `name`, `text`, timestamps, `related_cards` M2M)
  - `MemoryMaintenanceReport` (JSON report per maintenance run)
- Qdrant collection: `memories`
  - Constant defined in `app/appai/constants/storage.py`

Each memory is persisted in both Postgres and Qdrant:

- Postgres = source of truth + relational links to `Card`.
- Qdrant = dense-vector retrieval for semantic search.

## Deck-agent integration

- Main deck-constructor agent: `app/appai/services/agents/deck_constructor.py`
- Memory tools: `app/appai/services/agents/tools/memory_tools.py`
  - `write_memory`
  - `semantic_memory_search`
  - `card_memory_search`
  - `subagent_memory_search`
- Runtime dependency counters: `app/appai/services/agents/deps.py`
  - `memories_written`
  - `checked_memories`
  - `memory_searches`

---

## 3) Write path

When the main agent calls `write_memory`:

1. Related-card UUIDs are validated.
2. A helper subagent converts unstructured text into structured `Memory` output (`name`, `text`, `related_card_uuids`).
3. If output is accepted, memory is written to Postgres.
4. Dense embedding is generated from `text`.
5. Memory is upserted into Qdrant `memories` collection with payload metadata.

Important constraints:

- Maximum related card UUIDs per write: 10.
- The memory-writing subagent may refuse to write memory if content is not worth retaining.
- Memory content should be general and MTG-relevant, not user-personal.

---

## 4) Retrieval path

Retrieval is available through two lower-level tools plus one orchestrator tool:

- `semantic_memory_search(query)`
  - Natural-language vector search.
  - Returns up to 5 results.
- `card_memory_search(card_uuids)`
  - Filters by `related_card_uuids` payload.
- `subagent_memory_search(query)`
  - Calls one or both lower-level tools, then returns a concise memory-grounded summary.

Search controls:

- `MAX_MEMORY_SEARCHES = 10` per deck-construction run.
- Score threshold is applied (`MIN_RELEVANCE_SCORE = 0.5`).
- If no memories exist, tools return empty/safe defaults.

---

## 5) Deck-construction behavior

The deck-constructor prompt explicitly encourages memory usage:

- Early: check existing memories for relevant context.
- Late: consider writing new durable insights.

Output validation also nudges reflection:

- If the agent attempts to finish without checking/writing memories, it gets one reminder retry pass before output is accepted.

This encourages memory usage without making memory writes strictly mandatory.

---

## 6) Automated maintenance

Memory maintenance task:

- Task: `appai.tasks.memory_maintenance.run_memory_maintenance_task`
- Graph: `app/appai/services/graphs/memory_maintenance.py`
- Maintenance agent: `app/appai/services/agents/memory_maintenance.py`

Scheduled execution:

- Celery beat checks every 30 minutes (configured in `app/app/settings.py`).
- Task short-circuits if:
  - a maintenance report already exists for today, or
  - fewer than 10 new memories were created since last report.

Maintenance pipeline:

1. Retrieve Postgres memories and existing Qdrant vectors.
2. Re-embed any memory missing a usable vector.
3. Run UMAP dimensionality reduction.
4. Run HDBSCAN clustering.
5. For each cluster, ask maintenance agent to produce replacement memories.
6. Replace old cluster memories with new consolidated memories (Postgres + Qdrant).
7. Persist a `MemoryMaintenanceReport` summary.

---

## 7) Operations

Run maintenance immediately (local backend process):

```bash
cd /workspace/deep_mtg_2/app && /workspace/deep_mtg_2/.venv/bin/python manage.py shell -c "import asyncio; from appai.services.graphs.memory_maintenance import run_memory_maintenance; asyncio.run(run_memory_maintenance())"
```

Queue maintenance through Celery (Docker workflow):

```bash
docker compose exec web python app/manage.py shell -c "from appai.tasks.memory_maintenance import run_memory_maintenance_task; run_memory_maintenance_task.delay()"
```

Inspect recent reports:

```bash
cd /workspace/deep_mtg_2/app && /workspace/deep_mtg_2/.venv/bin/python manage.py shell -c "from appai.models.memory import MemoryMaintenanceReport; print(list(MemoryMaintenanceReport.objects.order_by('-created_at').values('created_at', 'report')[:5]))"
```

---

## 8) Testing references

Memory-related backend tests live under:

- `app/appai/tests/test_memory_model_and_tools.py`
- `app/appai/tests/test_memory_maintenance_agent.py`
- `app/appai/tests/test_memory_maintenance_graph.py`
- `app/appai/tests/test_task_memory_maintenance.py`

Run with Django test runner:

```bash
cd /workspace/deep_mtg_2/app && /workspace/deep_mtg_2/.venv/bin/python manage.py test appai.tests.test_memory_model_and_tools appai.tests.test_memory_maintenance_agent appai.tests.test_memory_maintenance_graph appai.tests.test_task_memory_maintenance
```
