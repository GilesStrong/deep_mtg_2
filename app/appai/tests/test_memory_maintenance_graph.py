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
from uuid import UUID

import numpy as np
from django.test import TestCase

from appai.dataclasses.memory import ExistingMemory
from appai.services.graphs import memory_maintenance as mm


def _make_existing_memory(memory_id: UUID, name: str, text: str) -> ExistingMemory:
    """Create a minimal ExistingMemory for graph tests.

    Args:
        memory_id: Memory identifier.
        name: Memory title.
        text: Memory body text.

    Returns:
        ExistingMemory: A typed memory test fixture.
    """
    return ExistingMemory(
        id=memory_id,
        name=name,
        text=text,
        related_card_uuids=set(),
        created_at="2026-01-01T00:00:00+00:00",
    )


def _make_pg_memory(memory_id: UUID, text: str) -> SimpleNamespace:
    """Create a minimal ORM-like memory object for retrieval tests.

    Args:
        memory_id: Memory identifier.
        text: Memory body text.

    Returns:
        SimpleNamespace: A lightweight PGMemory stand-in.
    """
    related_cards = SimpleNamespace(all=lambda: [])
    return SimpleNamespace(
        id=memory_id,
        name=f"Memory-{memory_id}",
        text=text,
        related_cards=related_cards,
        created_at=datetime.now(timezone.utc),
    )


class EmbeddedMemoriesTests(TestCase):
    def test_validate_consistency_raises_on_mismatched_lengths(self) -> None:
        """
        GIVEN mismatched memory and embedding lengths
        WHEN EmbeddedMemories is validated
        THEN it raises ValueError
        """
        first = _make_existing_memory(UUID("11111111-1111-1111-1111-111111111111"), "A", "a")
        second = _make_existing_memory(UUID("22222222-2222-2222-2222-222222222222"), "B", "b")

        with self.assertRaises(ValueError):
            mm.EmbeddedMemories(
                memories=[first, second],
                embeddings=np.array([[0.1, 0.2]], dtype=float),
            )


class RunHDBSCANNodeTests(TestCase):
    async def test_assigns_cluster_labels_and_transitions(self) -> None:
        """
        GIVEN UMAP coordinates are present in state
        WHEN RunHDBSCAN.run executes
        THEN it stores cluster assignments and transitions to MaintainClusteredMemories
        """
        first = _make_existing_memory(UUID("33333333-3333-3333-3333-333333333333"), "A", "a")
        second = _make_existing_memory(UUID("44444444-4444-4444-4444-444444444444"), "B", "b")
        state = mm.MemoryMaintenanceState(
            memories=mm.EmbeddedMemories(
                memories=[first, second],
                embeddings=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=float),
                umap_coords=np.array([[0.0, 0.0], [1.0, 1.0]], dtype=float),
            )
        )
        ctx = SimpleNamespace(state=state)

        mock_clusterer = MagicMock()
        mock_clusterer.fit_predict.return_value = np.array([2, 3], dtype=int)

        with patch.object(mm.hdbscan, "HDBSCAN", MagicMock(return_value=mock_clusterer)):
            result = await mm.RunHDBSCAN().run(ctx)

        self.assertIsInstance(result, mm.MaintainClusteredMemories)
        np.testing.assert_array_equal(state.memories.cluster_assignments, np.array([2, 3], dtype=int))

    async def test_raises_when_umap_coords_missing(self) -> None:
        """
        GIVEN graph state does not include UMAP coordinates
        WHEN RunHDBSCAN.run executes
        THEN it raises ValueError
        """
        memory = _make_existing_memory(UUID("55555555-5555-5555-5555-555555555555"), "A", "a")
        state = mm.MemoryMaintenanceState(
            memories=mm.EmbeddedMemories(
                memories=[memory],
                embeddings=np.array([[1.0, 2.0]], dtype=float),
            )
        )
        ctx = SimpleNamespace(state=state)

        with self.assertRaises(ValueError):
            await mm.RunHDBSCAN().run(ctx)


class MaintainClusteredMemoriesNodeTests(TestCase):
    async def test_aggregates_clusters_and_returns_compile_report(self) -> None:
        """
        GIVEN memories with precomputed cluster assignments
        WHEN MaintainClusteredMemories.run executes
        THEN it calls maintain_memories per cluster and returns CompileReport
        """
        first = _make_existing_memory(UUID("66666666-6666-6666-6666-666666666666"), "A", "a")
        second = _make_existing_memory(UUID("77777777-7777-7777-7777-777777777777"), "B", "b")
        third = _make_existing_memory(UUID("88888888-8888-8888-8888-888888888888"), "C", "c")
        state = mm.MemoryMaintenanceState(
            memories=mm.EmbeddedMemories(
                memories=[first, second, third],
                cluster_assignments=np.array([0, 0, 1], dtype=int),
            )
        )
        ctx = SimpleNamespace(state=state)

        maintain_mock = AsyncMock(side_effect=[2, 1])
        with patch.object(mm, "maintain_memories", maintain_mock):
            result = await mm.MaintainClusteredMemories().run(ctx)

        self.assertIsInstance(result, mm.CompileReport)
        self.assertEqual(result.new_memories_counts, [2, 1])
        self.assertEqual(len(result.clustered_memories[0]), 2)
        self.assertEqual(len(result.clustered_memories[1]), 1)
        self.assertEqual(maintain_mock.await_count, 2)


class RetrieveMemoriesNodeTests(TestCase):
    async def test_backfills_missing_qdrant_vectors_with_dense_embed(self) -> None:
        """
        GIVEN one memory missing a Qdrant dense vector
        WHEN RetrieveMemories.run executes
        THEN it backfills embedding data and transitions to RunUMAP
        """
        first_id = UUID("99999999-9999-9999-9999-999999999999")
        second_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        pg_memory_one = _make_pg_memory(first_id, "first")
        pg_memory_two = _make_pg_memory(second_id, "second")

        qdrant_memory = SimpleNamespace(id=str(first_id), vector={"dense": [0.25, 0.5]})
        prefetch_queryset = MagicMock()
        prefetch_queryset.all.return_value = [pg_memory_one, pg_memory_two]
        pg_memory_model = MagicMock()
        pg_memory_model.objects.prefetch_related.return_value = prefetch_queryset

        retrieve_mock = MagicMock(return_value=[qdrant_memory])
        dense_embed_mock = MagicMock(return_value=[0.75, 1.0])
        ctx = SimpleNamespace(state=mm.MemoryMaintenanceState())

        with (
            patch.object(mm, "PGMemory", pg_memory_model),
            patch.object(mm.QDRANT_CLIENT, "retrieve", retrieve_mock),
            patch.object(mm, "dense_embed", dense_embed_mock),
        ):
            result = await mm.RetrieveMemories().run(ctx)

        self.assertIsInstance(result, mm.RunUMAP)
        self.assertIsNotNone(ctx.state.memories)
        np.testing.assert_array_equal(
            ctx.state.memories.embeddings,
            np.array([[0.25, 0.5], [0.75, 1.0]], dtype=float),
        )
        dense_embed_mock.assert_called_once_with("second")
        retrieve_mock.assert_called_once()


class CompileReportNodeTests(TestCase):
    async def test_persists_report_payload(self) -> None:
        """
        GIVEN clustered and newly created memory counts
        WHEN CompileReport.run executes
        THEN it persists a maintenance report row
        """
        first = _make_existing_memory(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"), "A", "a")
        second = _make_existing_memory(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), "B", "b")
        node = mm.CompileReport(clustered_memories={0: [first], 1: [second]}, new_memories_counts=[3, 4])

        acreate_mock = AsyncMock()
        memory_report_model = MagicMock()
        memory_report_model.objects.acreate = acreate_mock

        with patch.object(mm, "MemoryMaintenanceReport", memory_report_model):
            result = await node.run(SimpleNamespace(state=None))

        self.assertEqual(result.__class__.__name__, "End")
        acreate_mock.assert_awaited_once_with(
            report={
                "n_clusters": 2,
                "n_old_memories": 2,
                "n_new_memories": 7,
                "n_old_memories_per_cluster": [1, 1],
                "n_new_memories_per_cluster": [3, 4],
            }
        )


class RunMemoryMaintenanceTests(TestCase):
    async def test_builds_graph_and_runs_from_retrieve_memories(self) -> None:
        """
        GIVEN the run_memory_maintenance entrypoint is called
        WHEN orchestration executes
        THEN Graph.run starts from RetrieveMemories with initialized state
        """
        graph_instance = MagicMock()
        graph_instance.run = AsyncMock()
        graph_cls = MagicMock(return_value=graph_instance)

        with patch.object(mm, "Graph", graph_cls):
            await mm.run_memory_maintenance()

        graph_cls.assert_called_once_with(
            nodes=[
                mm.RetrieveMemories,
                mm.RunUMAP,
                mm.RunHDBSCAN,
                mm.MaintainClusteredMemories,
                mm.CompileReport,
            ],
            state_type=mm.MemoryMaintenanceState,
        )
        graph_instance.run.assert_awaited_once()
        call_args = graph_instance.run.call_args
        self.assertIsInstance(call_args.args[0], mm.RetrieveMemories)
        self.assertIsInstance(call_args.kwargs["state"], mm.MemoryMaintenanceState)
