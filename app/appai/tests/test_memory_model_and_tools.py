# Copyright 2026 Giles Strong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from django.test import TestCase
from pydantic_ai import ModelRetry

from appai.constants.storage import MEMORY_COLLECTION_NAME
from appai.models.memory import Memory as PGMemory
from appai.services.agents.tools.memory_tools import (
    MAX_MEMORY_SEARCHES,
    MIN_RELEVANCE_SCORE,
    card_memory_search,
    semantic_memory_search,
    write_memory,
)

_MODEL_MODULE = "appai.models.memory"
_TOOLS_MODULE = "appai.services.agents.tools.memory_tools"


def _build_ctx(*, memory_searches: int = 0, memories_written: int = 0) -> SimpleNamespace:
    """Build a minimal context object for memory tool calls in tests.

    Args:
        memory_searches (int): Number of searches already used in the current run.
        memories_written (int): Number of memories already written in the current run.

    Returns:
        SimpleNamespace: A context-like object exposing deps with required counters.
    """
    return SimpleNamespace(
        deps=SimpleNamespace(
            memory_searches=memory_searches,
            memories_written=memories_written,
        )
    )


class MemoryModelTests(TestCase):
    @patch(f"{_MODEL_MODULE}.QDRANT_CLIENT")
    def test_delete_removes_vector_point_and_row(self, mock_client):
        """
        GIVEN a persisted memory
        WHEN it is deleted
        THEN the corresponding vector point is deleted from Qdrant and the row is removed
        """
        memory = PGMemory.objects.create(name="Tempo Insight", text="Keep two-mana interaction density high")
        memory_id = str(memory.id)

        memory.delete()

        mock_client.delete.assert_called_once_with(
            collection_name=MEMORY_COLLECTION_NAME,
            points_selector=[memory_id],
        )
        self.assertFalse(PGMemory.objects.filter(id=memory.id).exists())


class SemanticMemorySearchTests(TestCase):
    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_returns_empty_when_memory_collection_has_no_points(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN an empty memory collection
        WHEN semantic_memory_search is called
        THEN it returns no memories without running the DSL query
        """
        mock_qdrant_client.count.return_value = SimpleNamespace(count=0)
        ctx = _build_ctx()

        result = await semantic_memory_search(ctx, "find interaction synergies")

        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)
        self.assertEqual(result.total_memories, 0)
        self.assertEqual(result.memories, [])
        self.assertEqual(ctx.deps.memory_searches, 0)
        mock_run_query.assert_not_called()

    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_forwards_score_threshold_and_parses_payloads(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN stored memories and search results with one missing payload
        WHEN semantic_memory_search is called
        THEN it applies the minimum relevance threshold and returns parsed memory objects
        """
        related_uuid = uuid4()
        mock_qdrant_client.count.return_value = SimpleNamespace(count=3)
        mock_run_query.return_value = [
            SimpleNamespace(
                payload={
                    "name": "Go-wide pressure",
                    "text": "Token payoffs overperform in grindy mirrors",
                    "related_card_uuids": [str(related_uuid)],
                }
            ),
            SimpleNamespace(payload=None),
        ]
        ctx = _build_ctx()

        result = await semantic_memory_search(ctx, "token mirror matchups")

        self.assertEqual(result.total_memories, 3)
        self.assertEqual(len(result.memories), 1)
        self.assertEqual(result.memories[0].name, "Go-wide pressure")
        self.assertEqual(result.memories[0].related_card_uuids, {related_uuid})
        self.assertEqual(ctx.deps.memory_searches, 1)

        query_arg = mock_run_query.call_args.args[0]
        self.assertEqual(query_arg.collection_name, MEMORY_COLLECTION_NAME)
        self.assertEqual(query_arg.query_string, "token mirror matchups")
        self.assertEqual(mock_run_query.call_args.kwargs["score_threshold"], MIN_RELEVANCE_SCORE)
        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)

    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_raises_when_search_budget_is_exhausted(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN the per-run memory search budget is exhausted
        WHEN semantic_memory_search is called
        THEN it raises ModelRetry and skips running the DSL query
        """
        mock_qdrant_client.count.return_value = SimpleNamespace(count=3)
        ctx = _build_ctx(memory_searches=MAX_MEMORY_SEARCHES)

        with self.assertRaises(ModelRetry):
            await semantic_memory_search(ctx, "find control matchup insights")

        self.assertEqual(ctx.deps.memory_searches, MAX_MEMORY_SEARCHES)
        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)
        mock_qdrant_client.count.assert_called_once_with(collection_name=MEMORY_COLLECTION_NAME)
        mock_run_query.assert_not_called()


class CardMemorySearchTests(TestCase):
    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_returns_empty_for_empty_card_list(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN a non-empty memory collection and no card UUIDs
        WHEN card_memory_search is called
        THEN it returns no memories and does not run the DSL query
        """
        mock_qdrant_client.count.return_value = SimpleNamespace(count=5)
        ctx = _build_ctx()

        result = await card_memory_search(ctx, [])

        self.assertEqual(result.total_memories, 5)
        self.assertEqual(result.memories, [])
        self.assertEqual(ctx.deps.memory_searches, 1)
        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)
        mock_run_query.assert_not_called()

    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_builds_related_card_filter_and_uses_score_threshold(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN card UUIDs and matching memory search results
        WHEN card_memory_search is called
        THEN it builds a card UUID filter and forwards minimum relevance threshold
        """
        first_card = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        second_card = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        mock_qdrant_client.count.return_value = SimpleNamespace(count=2)
        mock_run_query.return_value = [
            SimpleNamespace(
                payload={
                    "name": "Prowess sequencing",
                    "text": "Cheap cantrips improve trigger density",
                    "related_card_uuids": [str(first_card), str(second_card)],
                }
            )
        ]
        ctx = _build_ctx()

        result = await card_memory_search(ctx, [first_card, second_card])

        self.assertEqual(result.total_memories, 2)
        self.assertEqual(len(result.memories), 1)
        query_arg = mock_run_query.call_args.args[0]
        self.assertIsNotNone(query_arg.filter)
        self.assertEqual(query_arg.filter.min_should_count, 1)
        self.assertEqual(query_arg.filter.should[0].key, "related_card_uuids")
        self.assertEqual(query_arg.filter.should[0].any, [str(first_card), str(second_card)])
        self.assertEqual(mock_run_query.call_args.kwargs["score_threshold"], MIN_RELEVANCE_SCORE)
        self.assertEqual(ctx.deps.memory_searches, 1)
        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)

    @patch(f"{_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_TOOLS_MODULE}.QDRANT_CLIENT")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_raises_when_search_budget_is_exhausted(
        self,
        mock_create_collection,
        mock_qdrant_client,
        mock_run_query,
    ):
        """
        GIVEN the per-run memory search budget is exhausted
        WHEN card_memory_search is called
        THEN it raises ModelRetry and skips collection/query work
        """
        ctx = _build_ctx(memory_searches=MAX_MEMORY_SEARCHES)

        with self.assertRaises(ModelRetry):
            await card_memory_search(ctx, [uuid4()])

        self.assertEqual(ctx.deps.memory_searches, MAX_MEMORY_SEARCHES)
        mock_create_collection.assert_not_called()
        mock_qdrant_client.count.assert_not_called()
        mock_run_query.assert_not_called()


class WriteMemoryTests(TestCase):
    @patch(f"{_TOOLS_MODULE}.upsert_documents")
    @patch(f"{_TOOLS_MODULE}.dense_embed")
    @patch(f"{_TOOLS_MODULE}.PGMemory")
    @patch(f"{_TOOLS_MODULE}.Agent")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_refused_memory_is_not_persisted(
        self,
        mock_create_collection,
        mock_agent_cls,
        mock_pg_memory,
        mock_dense_embed,
        mock_upsert_documents,
    ):
        """
        GIVEN the memory-writing subagent refuses to emit a memory
        WHEN write_memory is called
        THEN no database create or vector upsert occurs
        """
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=SimpleNamespace(output=None))
        mock_agent_cls.return_value = mock_agent
        mock_pg_memory.objects.acreate = AsyncMock()
        ctx = _build_ctx()

        await write_memory(ctx, "User likes this deck and had fun piloting it", set())

        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)
        self.assertEqual(mock_agent_cls.call_args.kwargs["retries"], 10)
        self.assertEqual(mock_agent_cls.call_args.kwargs["output_retries"], 10)
        mock_pg_memory.objects.acreate.assert_not_awaited()
        mock_dense_embed.assert_not_called()
        mock_upsert_documents.assert_not_called()
        self.assertEqual(ctx.deps.memories_written, 0)

    @patch(f"{_TOOLS_MODULE}._check_related_card_uuids", new_callable=AsyncMock)
    @patch(f"{_TOOLS_MODULE}.upsert_documents")
    @patch(f"{_TOOLS_MODULE}.dense_embed")
    @patch(f"{_TOOLS_MODULE}.PGMemory")
    @patch(f"{_TOOLS_MODULE}.Agent")
    @patch(f"{_TOOLS_MODULE}.create_collection_if_not_exists")
    async def test_persists_memory_and_upserts_vector_point(
        self,
        mock_create_collection,
        mock_agent_cls,
        mock_pg_memory,
        mock_dense_embed,
        mock_upsert_documents,
        mock_check_related_card_uuids,
    ):
        """
        GIVEN a valid structured memory output from the writing subagent
        WHEN write_memory is called
        THEN it persists the memory and upserts a vector point with matching payload
        """
        related_uuid = UUID("11111111-1111-1111-1111-111111111111")
        explicit_related_uuid = UUID("33333333-3333-3333-3333-333333333333")
        output = SimpleNamespace(
            name="Tempo mirror heuristic",
            text="Prioritise one-mana interaction to avoid falling behind on board",
            related_card_uuids={related_uuid},
        )

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=SimpleNamespace(output=output))
        mock_agent_cls.return_value = mock_agent

        created_at = datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc)
        memory_id = UUID("22222222-2222-2222-2222-222222222222")
        related_cards_manager = SimpleNamespace(aadd=AsyncMock())
        mock_pg_memory.objects.acreate = AsyncMock(
            return_value=SimpleNamespace(
                id=memory_id,
                name=output.name,
                text=output.text,
                related_cards=related_cards_manager,
                created_at=created_at,
            )
        )
        mock_dense_embed.return_value = [0.12, 0.34, 0.56]
        ctx = _build_ctx()

        await write_memory(ctx, "Store durable tempo-sideboarding insight", {explicit_related_uuid})

        mock_create_collection.assert_called_once_with(MEMORY_COLLECTION_NAME)
        self.assertEqual(mock_agent_cls.call_args.kwargs["retries"], 10)
        self.assertEqual(mock_agent_cls.call_args.kwargs["output_retries"], 10)
        mock_pg_memory.objects.acreate.assert_awaited_once_with(
            name=output.name,
            text=output.text,
        )
        related_cards_manager.aadd.assert_awaited_once()
        self.assertEqual(
            set(related_cards_manager.aadd.await_args.args),
            {related_uuid, explicit_related_uuid},
        )
        mock_check_related_card_uuids.assert_awaited_once_with({explicit_related_uuid})
        mock_dense_embed.assert_called_once_with(output.text)

        self.assertEqual(mock_upsert_documents.call_args.kwargs["collection_name"], MEMORY_COLLECTION_NAME)
        points = mock_upsert_documents.call_args.kwargs["points"]
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].id, str(memory_id))
        self.assertEqual(
            set(points[0].payload["related_card_uuids"]),
            {str(related_uuid), str(explicit_related_uuid)},
        )
        self.assertEqual(ctx.deps.memories_written, 1)
