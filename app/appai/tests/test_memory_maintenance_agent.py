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

from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase
from pydantic_ai import ModelRetry

from appai.dataclasses.memory import ExistingMemory, Memory
from appai.services.agents import memory_maintenance as mm


def _make_existing_memory(memory_id: UUID, name: str, text: str) -> ExistingMemory:
    """Create a minimal ExistingMemory fixture.

    Args:
        memory_id: Memory identifier.
        name: Memory title.
        text: Memory body text.

    Returns:
        ExistingMemory: A fixture instance.
    """
    return ExistingMemory(
        id=memory_id,
        name=name,
        text=text,
        related_card_uuids=set(),
        created_at="2026-01-01T00:00:00+00:00",
    )


def _make_new_memory(name: str, text: str) -> Memory:
    """Create a minimal new Memory fixture.

    Args:
        name: Memory title.
        text: Memory body text.

    Returns:
        Memory: A fixture instance.
    """
    return Memory(name=name, text=text, related_card_uuids=set())


def _sync_to_async_passthrough(fn: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """Wrap a sync callable in an awaitable passthrough.

    Args:
        fn: Synchronous callable.

    Returns:
        Callable[..., Awaitable[Any]]: Async callable invoking ``fn``.
    """

    async def _runner(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    return _runner


class _FakeAgent:
    """Test double for pydantic_ai.Agent.

    The fake stores the registered output validator and applies it to a
    preconfigured output payload when ``run`` is called.
    """

    next_output: list[Memory] = []
    last_run_messages: list[str] = []
    last_kwargs: dict[str, Any] = {}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize fake agent and capture construction kwargs.

        Args:
            **kwargs: Agent constructor kwargs.
        """
        self._validator: Callable[[list[Memory]], Awaitable[list[Memory]]] | None = None
        _FakeAgent.last_kwargs = dict(kwargs)

    def output_validator(
        self, fn: Callable[[list[Memory]], Awaitable[list[Memory]]]
    ) -> Callable[[list[Memory]], Awaitable[list[Memory]]]:
        """Register an output validator callback.

        Args:
            fn: Validator coroutine.

        Returns:
            Callable[[list[Memory]], Awaitable[list[Memory]]]: The same callback.
        """
        self._validator = fn
        return fn

    async def run(self, messages: list[str]) -> SimpleNamespace:
        """Execute fake agent run using preconfigured output.

        Args:
            messages: Prompt messages.

        Returns:
            SimpleNamespace: Object exposing the ``output`` attribute.
        """
        _FakeAgent.last_run_messages = list(messages)
        output = _FakeAgent.next_output
        if self._validator is not None:
            output = await self._validator(output)
        return SimpleNamespace(output=output)


class MaintainMemoriesTests(TestCase):
    async def test_returns_count_and_updates_memories_on_valid_output(self) -> None:
        """
        GIVEN a valid cluster and valid agent output
        WHEN maintain_memories executes
        THEN it updates persisted memories and returns output count
        """
        clustered = [_make_existing_memory(UUID("11111111-1111-1111-1111-111111111111"), "Old", "old text")]
        output = [_make_new_memory("New", "new text")]

        card_queryset = MagicMock()
        card_queryset.filter.return_value = []
        card_model = MagicMock()
        card_model.objects.prefetch_related.return_value = card_queryset

        update_mock = MagicMock()
        check_uuids_mock = AsyncMock(return_value=None)

        _FakeAgent.next_output = output

        with (
            patch.object(mm, "Agent", new=_FakeAgent),
            patch.object(mm, "Card", card_model),
            patch.object(mm, "sync_to_async", _sync_to_async_passthrough),
            patch.object(mm, "_check_related_card_uuids", check_uuids_mock),
            patch.object(mm, "update_memories", update_mock),
        ):
            result = await mm.maintain_memories(clustered)

        self.assertEqual(result, 1)
        update_mock.assert_called_once_with(clustered, output)
        check_uuids_mock.assert_awaited_once_with(set())
        self.assertIn("current set of legal set codes in Standard", _FakeAgent.last_run_messages[0])
        self.assertIn("Memory 1:", _FakeAgent.last_run_messages[1])

    async def test_raises_when_agent_outputs_too_many_memories(self) -> None:
        """
        GIVEN one input memory and two output memories
        WHEN maintain_memories validates output
        THEN it raises ModelRetry and does not update storage
        """
        clustered = [_make_existing_memory(UUID("22222222-2222-2222-2222-222222222222"), "Old", "old text")]
        _FakeAgent.next_output = [_make_new_memory("A", "a"), _make_new_memory("B", "b")]

        card_queryset = MagicMock()
        card_queryset.filter.return_value = []
        card_model = MagicMock()
        card_model.objects.prefetch_related.return_value = card_queryset

        update_mock = MagicMock()

        with (
            patch.object(mm, "Agent", new=_FakeAgent),
            patch.object(mm, "Card", card_model),
            patch.object(mm, "sync_to_async", _sync_to_async_passthrough),
            patch.object(mm, "update_memories", update_mock),
        ):
            with self.assertRaises(ModelRetry):
                await mm.maintain_memories(clustered)

        update_mock.assert_not_called()

    async def test_raises_when_output_contains_invalid_related_card_uuids(self) -> None:
        """
        GIVEN output with invalid related card UUIDs
        WHEN maintain_memories validates output
        THEN it raises ModelRetry and does not update storage
        """
        clustered = [_make_existing_memory(UUID("33333333-3333-3333-3333-333333333333"), "Old", "old text")]
        _FakeAgent.next_output = [_make_new_memory("New", "new text")]

        card_queryset = MagicMock()
        card_queryset.filter.return_value = []
        card_model = MagicMock()
        card_model.objects.prefetch_related.return_value = card_queryset

        update_mock = MagicMock()
        check_uuids_mock = AsyncMock(side_effect=mm.CardValidationError("invalid uuid"))

        with (
            patch.object(mm, "Agent", new=_FakeAgent),
            patch.object(mm, "Card", card_model),
            patch.object(mm, "sync_to_async", _sync_to_async_passthrough),
            patch.object(mm, "_check_related_card_uuids", check_uuids_mock),
            patch.object(mm, "update_memories", update_mock),
        ):
            with self.assertRaises(ModelRetry):
                await mm.maintain_memories(clustered)

        update_mock.assert_not_called()


class UpdateMemoriesTests(TestCase):
    def test_deletes_old_rows_and_upserts_new_vectors(self) -> None:
        """
        GIVEN old memories and replacement memories
        WHEN update_memories executes
        THEN old DB/vector rows are removed and replacement vectors are upserted
        """
        existing = [_make_existing_memory(UUID("44444444-4444-4444-4444-444444444444"), "Old", "old text")]
        new_memories = [_make_new_memory("New", "new text")]

        old_filter_queryset = MagicMock()
        old_filter_queryset.delete = MagicMock()

        created_memory = SimpleNamespace(
            id=UUID("55555555-5555-5555-5555-555555555555"),
            name="New",
            text="new text",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            related_cards=SimpleNamespace(all=lambda: []),
        )

        pg_manager = MagicMock()
        pg_manager.filter.return_value = old_filter_queryset
        pg_manager.bulk_create.return_value = [created_memory]

        def _pg_memory_factory(*, name: str, text: str) -> SimpleNamespace:
            return SimpleNamespace(name=name, text=text, related_cards=SimpleNamespace(add=MagicMock(), all=lambda: []))

        pg_model = MagicMock(side_effect=_pg_memory_factory)
        pg_model.objects = pg_manager

        upsert_mock = MagicMock()
        point_struct_mock = MagicMock(side_effect=lambda **kwargs: kwargs)
        delete_mock = MagicMock()

        with (
            patch.object(mm.transaction, "atomic", return_value=nullcontext()),
            patch.object(mm, "PGMemory", pg_model),
            patch.object(mm, "dense_embed", MagicMock(return_value=[0.1, 0.2])),
            patch.object(mm, "upsert_documents", upsert_mock),
            patch.object(mm.qm, "PointStruct", point_struct_mock),
            patch.object(mm.QDRANT_CLIENT, "delete", delete_mock),
        ):
            mm.update_memories(existing, new_memories)

        pg_manager.filter.assert_called_once_with(id__in=[existing[0].id])
        old_filter_queryset.delete.assert_called_once_with()
        delete_mock.assert_called_once_with(
            collection_name=mm.MEMORY_COLLECTION_NAME,
            points_selector=[str(existing[0].id)],
        )
        upsert_mock.assert_called_once()

        upsert_args = upsert_mock.call_args.kwargs
        self.assertEqual(upsert_args["points"][0]["payload"]["name"], "New")
        self.assertEqual(upsert_args["points"][0]["vector"], {"dense": [0.1, 0.2]})
