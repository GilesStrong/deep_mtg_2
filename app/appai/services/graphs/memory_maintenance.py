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

import asyncio
from asyncio import Semaphore
from collections import defaultdict
from dataclasses import dataclass
from typing import Self, cast
from uuid import UUID

import hdbscan
import logfire
import numpy as np
import umap
from app.app_settings import APP_SETTINGS
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.client import QDRANT_CLIENT
from asgiref.sync import sync_to_async
from jaxtyping import Float, Int, jaxtyped
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from tenacity import retry, stop_after_attempt, wait_exponential

from appai.constants.storage import MEMORY_COLLECTION_NAME
from appai.dataclasses.memory import ExistingMemory
from appai.models.memory import Memory as PGMemory
from appai.models.memory import MemoryMaintenanceReport
from appai.modules.dense_embedding import dense_embed
from appai.services.agents.memory_maintenance import maintain_memories

MAX_CONCURRENCY = 8

UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1
UMAP_N_COMPONENTS = 2
UMAP_METRIC = "cosine"
UMAP_RANDOM_STATE = 42

HDBSCAN_MIN_CLUSTER_SIZE = 3
HDBSCAN_MIN_SAMPLES = 1
HDBSCAN_METRIC = "euclidean"
HDBSCAN_CLUSTER_SELECTION_METHOD = "eom"


class EmbeddedMemories(BaseModel):
    """Container for memories and their derived vector representations.

    This model stores the raw memory records together with optional embedding,
    dimensionality-reduced coordinates, and cluster assignments used by the
    maintenance pipeline.
    """

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)
    memories: list[ExistingMemory] = Field(
        default_factory=list,
        description="A list of memories that have been embedded with their vector representations.",
    )
    embeddings: np.ndarray | None = Field(
        default=None,
        description="A list of vector embeddings corresponding to the memories, where each embedding is a list of floats.",
    )
    umap_coords: np.ndarray | None = Field(
        default=None,
        description="The UMAP coordinates of the embedded memories, used for dimensionality reduction and visualization.",
    )
    cluster_assignments: np.ndarray | None = Field(
        default=None,
        description="A list of cluster assignments for each memory, where each assignment is an integer representing the cluster to which the memory belongs after applying HDBSCAN clustering.",
    )

    @field_validator("embeddings", "umap_coords", mode="after")
    @classmethod
    @jaxtyped(typechecker=beartype)
    def validate_embeddings(
        cls, v: Float[np.ndarray, "num_memories dim"] | None
    ) -> Float[np.ndarray, "num_memories dim"] | None:
        """Validate embedding-shaped arrays.

        Args:
            v: Embeddings or UMAP coordinates to validate.

        Returns:
            The validated value.
        """
        return v

    @field_validator("cluster_assignments", mode="after")
    @classmethod
    @jaxtyped(typechecker=beartype)
    def validate_cluster_assignments(
        cls, v: Int[np.ndarray, "num_memories 1"] | None
    ) -> Int[np.ndarray, "num_memories 1"] | None:
        """Validate cluster assignment array shape.

        Args:
            v: Cluster assignment array.

        Returns:
            The validated assignment array.
        """
        return v

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        """Ensure optional arrays align with memory count.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any optional array length differs from the number of
                memory items.
        """
        if self.embeddings is not None and len(self.embeddings) != len(self.memories):
            raise ValueError("Length of embeddings must match length of memories.")
        if self.umap_coords is not None and len(self.umap_coords) != len(self.memories):
            raise ValueError("Length of UMAP coordinates must match length of memories.")
        if self.cluster_assignments is not None and len(self.cluster_assignments) != len(self.memories):
            raise ValueError("Length of cluster assignments must match length of memories.")
        return self


class MemoryMaintenanceState(BaseModel):
    """Graph state carrying embedded memories through each node."""

    memories: EmbeddedMemories | None = Field(default=None, description="The list of memories with their embeddings.")


@dataclass
class CompileReport(BaseNode[MemoryMaintenanceState, None, None]):
    """Persist aggregate maintenance metrics after clustering completes."""

    clustered_memories: dict[int, list[ExistingMemory]]
    new_memories_counts: list[int]

    async def run(self, ctx: GraphRunContext[MemoryMaintenanceState]) -> End[None]:
        """Create and store a maintenance summary report.

        Args:
            ctx: Graph execution context containing maintenance state.

        Returns:
            Graph terminal node marker.
        """
        report = {
            "n_clusters": len(self.clustered_memories),
            "n_old_memories": sum(len(memories) for memories in self.clustered_memories.values()),
            "n_new_memories": sum(self.new_memories_counts),
            "n_old_memories_per_cluster": [len(memories) for memories in self.clustered_memories.values()],
            "n_new_memories_per_cluster": self.new_memories_counts,
        }
        logfire.info(f"Memory maintenance report: {report}")
        await MemoryMaintenanceReport.objects.acreate(report=report)
        return End(None)


@dataclass
class MaintainClusteredMemories(BaseNode[MemoryMaintenanceState]):
    """Run per-cluster memory maintenance with bounded concurrency."""

    async def run(self, ctx: GraphRunContext[MemoryMaintenanceState]) -> CompileReport:
        """Maintain memories for each discovered cluster.

        Args:
            ctx: Graph execution context containing clustered memory inputs.

        Returns:
            The report compilation node with cluster-level outputs.

        Raises:
            ValueError: If memories or cluster assignments are missing.
        """
        if ctx.state.memories is None or ctx.state.memories.cluster_assignments is None:
            message = (
                "Memories and their cluster assignments must be set in the state before maintaining clustered memories."
            )
            logfire.error(message)
            raise ValueError(message)

        # Aggregate memories by their cluster assignments
        clustered_memories: dict[int, list[ExistingMemory]] = defaultdict(list)
        for memory, cluster_id in zip(ctx.state.memories.memories, ctx.state.memories.cluster_assignments, strict=True):
            clustered_memories[cluster_id].append(memory)
        logfire.info(f"Found {len(clustered_memories)} unique clusters in {len(ctx.state.memories.memories)} memories.")

        # Maintain each cluster
        semaphore = Semaphore(MAX_CONCURRENCY)

        @retry(
            stop=stop_after_attempt(APP_SETTINGS.DECK_BUILD_RETRY_LIMIT),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        )
        async def _run_maintain_clustered_memories(memory_cluster: list[ExistingMemory]) -> int:
            """Maintain a single memory cluster under concurrency control.

            Args:
                memory_cluster: Memories belonging to one cluster.

            Returns:
                Number of newly created memories from maintenance.
            """
            async with semaphore:
                n_new_memories = await maintain_memories(memory_cluster)
                return n_new_memories

        new_memories_counts = await asyncio.gather(
            *[_run_maintain_clustered_memories(cluster) for cluster in clustered_memories.values()]
        )
        return CompileReport(clustered_memories=clustered_memories, new_memories_counts=new_memories_counts)


@dataclass
class RunHDBSCAN(BaseNode[MemoryMaintenanceState]):
    """Cluster UMAP coordinates using HDBSCAN."""

    async def run(self, ctx: GraphRunContext[MemoryMaintenanceState]) -> MaintainClusteredMemories:
        """Assign each memory to an HDBSCAN cluster.

        Args:
            ctx: Graph execution context containing UMAP coordinates.

        Returns:
            The node that performs cluster-level maintenance.

        Raises:
            ValueError: If UMAP coordinates are unavailable.
        """
        if ctx.state.memories is None or ctx.state.memories.umap_coords is None:
            message = "Memories and their UMAP coordinates must be set in the state before running HDBSCAN."
            logfire.error(message)
            raise ValueError(message)
        hdb_clusters = hdbscan.HDBSCAN(
            min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
            min_samples=HDBSCAN_MIN_SAMPLES,
            metric=HDBSCAN_METRIC,
            cluster_selection_method=HDBSCAN_CLUSTER_SELECTION_METHOD,
        ).fit_predict(ctx.state.memories.umap_coords)
        ctx.state.memories.cluster_assignments = hdb_clusters
        return MaintainClusteredMemories()


@dataclass
class RunUMAP(BaseNode[MemoryMaintenanceState]):
    """Project dense embeddings into a lower-dimensional manifold."""

    async def run(self, ctx: GraphRunContext[MemoryMaintenanceState]) -> RunHDBSCAN:
        """Run UMAP and normalize resulting coordinates.

        Args:
            ctx: Graph execution context containing embedding vectors.

        Returns:
            The node responsible for HDBSCAN clustering.

        Raises:
            ValueError: If embeddings are missing or UMAP output is invalid.
        """
        if ctx.state.memories is None or ctx.state.memories.embeddings is None:
            message = "Memories and their embeddings must be set in the state before running UMAP."
            logfire.error(message)
            raise ValueError(message)
        coords = umap.UMAP(
            n_neighbors=UMAP_N_NEIGHBORS,
            min_dist=UMAP_MIN_DIST,
            n_components=UMAP_N_COMPONENTS,
            metric=UMAP_METRIC,
            random_state=UMAP_RANDOM_STATE,
        ).fit_transform(ctx.state.memories.embeddings)
        if not isinstance(coords, np.ndarray):
            message = f"UMAP did not return a numpy array of coordinates. Got type {type(coords)} instead."
            logfire.error(message)
            raise ValueError("RunUMAP failed to generate UMAP coordinates for the memories.")
        coords = (coords - coords.mean(axis=0)) / coords.std(axis=0)
        ctx.state.memories.umap_coords = coords
        return RunHDBSCAN()


@dataclass
class RetrieveMemories(BaseNode[MemoryMaintenanceState]):
    """Load memories and ensure each has an embedding vector."""

    async def run(self, ctx: GraphRunContext[MemoryMaintenanceState]) -> RunUMAP:
        """Fetch memory records and their vectors from storage.

        Missing vectors are generated on demand with the dense embedding model.

        Args:
            ctx: Graph execution context to populate with embedded memories.

        Returns:
            The node that performs UMAP dimensionality reduction.
        """
        pg_memories = list(PGMemory.objects.prefetch_related("related_cards").all())
        qdrant_memories = await sync_to_async(QDRANT_CLIENT.retrieve)(
            collection_name=MEMORY_COLLECTION_NAME,
            ids=[str(memory.id) for memory in pg_memories],
            with_payload=False,
            with_vectors=True,
        )

        embedded_memories: list[ExistingMemory] = []
        memory_ids: list[UUID] = []
        embeddings: list[list[float]] = []
        for memory in pg_memories:
            qdrant_memory = next((m for m in qdrant_memories if m.id == str(memory.id)), None)
            if qdrant_memory is None:
                logfire.warning(f"Memory with ID {memory.id} not found in Qdrant.")
            vector = None
            if qdrant_memory is not None:
                if qdrant_memory.vector is not None:
                    if isinstance(qdrant_memory.vector, dict):
                        vector = qdrant_memory.vector.get('dense')
                        if vector is None:
                            logfire.warning(f"Memory with ID {memory.id} has no 'dense' vector in Qdrant.")
                        elif not isinstance(vector, list) or len(vector) == 0 or not isinstance(vector[0], float):
                            logfire.warning(
                                f"Memory with ID {memory.id} has a 'dense' vector in Qdrant that is not a list of floats."
                            )
                            vector = None
                        else:
                            vector = cast(list[float], vector)
                    else:
                        logfire.warning(f"Memory with ID {memory.id} has a non-dict vector in Qdrant.")
                else:
                    logfire.warning(f"Memory with ID {memory.id} has no vector in Qdrant.")
            if vector is None:
                logfire.info(f"Generating embedding for memory with ID {memory.id}.")
                vector = dense_embed(memory.text)

            embedded_memories.append(
                ExistingMemory(
                    id=memory.id,
                    name=memory.name,
                    text=memory.text,
                    related_card_uuids={UUID(card.uuid) for card in memory.related_cards.all()},
                    created_at=memory.created_at.isoformat(),
                )
            )
            memory_ids.append(memory.id)
            embeddings.append(vector)  # type: ignore[arg-type]

        ctx.state.memories = EmbeddedMemories(memories=embedded_memories, embeddings=np.array(embeddings))
        return RunUMAP()


async def run_memory_maintenance() -> None:
    """Execute the memory maintenance graph end to end."""

    memory_maintenance_graph = Graph(
        nodes=[RetrieveMemories, RunUMAP, RunHDBSCAN, MaintainClusteredMemories, CompileReport],
        state_type=MemoryMaintenanceState,
    )
    state = MemoryMaintenanceState()

    await memory_maintenance_graph.run(RetrieveMemories(), state=state)
