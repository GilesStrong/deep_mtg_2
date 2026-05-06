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

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from typing import Any, Callable

from appcards.constants.storage import CARD_COLLECTION_NAME, THEME_COLLECTION_NAME
from appcards.models.card import Card
from appcards.models.deck import DailyDeckTheme
from appcards.modules.card_to_qm_pointstruct import card_to_qm_pointstruct
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.client import QDRANT_CLIENT
from appsearch.services.qdrant.upsert import create_collection_if_not_exists, upsert_documents
from django.core.management.base import BaseCommand
from qdrant_client.http import models as qm
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from appai.constants.storage import MEMORY_COLLECTION_NAME
from appai.models.memory import Memory
from appai.modules.dense_embedding import dense_embed


def _re_embed_items(
    items: list[Any],
    item_to_point: Callable[[Any], qm.PointStruct],
    item_label: Callable[[Any], str],
    collection_name: str,
    batchsize: int,
    max_workers: int,
) -> None:
    """Re-embed a list of items into a Qdrant collection.

    Deletes and recreates the collection, then embeds all items in batches
    using a thread pool. Failed embeddings are logged and skipped.

    Args:
        items: Items to embed.
        item_to_point: Converts a single item to a Qdrant PointStruct.
        item_label: Returns a display label for an item (used in log output).
        collection_name: Target Qdrant collection name.
        batchsize: Number of items per upsert batch.
        max_workers: Maximum concurrent embedding threads.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def embed_item(item: Any, semaphore: Semaphore) -> qm.PointStruct:
        """Embed a single item, acquiring the semaphore before calling the API.

        Args:
            item: The item to embed.
            semaphore: Semaphore limiting concurrent API calls.

        Returns:
            A Qdrant PointStruct for the item.
        """
        with semaphore:
            point = item_to_point(item)
            print(f"✓ Generated embedding for: {item_label(item)}")
            return point

    def _embed_batch(batch: list[Any]) -> None:
        """Embed a batch of items concurrently and upsert results to Qdrant.

        Args:
            batch: Items to embed in this batch.
        """
        semaphore = Semaphore(max_workers)
        embedding_results: list[qm.PointStruct] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(embed_item, item, semaphore) for item in batch]
            for future in as_completed(futures):
                try:
                    embedding_results.append(future.result())
                except Exception as e:
                    print(f"✗ Failed to generate embedding: {e}")
        if embedding_results:
            upsert_documents(collection_name=collection_name, points=embedding_results)

    def get_un_embedded(all_items: list[Any]) -> list[Any]:
        """Return items that do not yet have a vector in the collection.

        Args:
            all_items: Full list of items to check.

        Returns:
            Items whose IDs are absent from the Qdrant collection.
        """
        existing_points = QDRANT_CLIENT.retrieve(
            collection_name=collection_name,
            ids=[str(item.id) for item in all_items],
            with_payload=True,
            with_vectors=False,
        )
        existing_ids = {str(p.id) for p in existing_points}
        return [item for item in all_items if str(item.id) not in existing_ids]

    batchsize = max(1, batchsize)
    if collection_name in [c.name for c in QDRANT_CLIENT.get_collections().collections]:
        QDRANT_CLIENT.delete_collection(collection_name=collection_name)
    assert collection_name not in [c.name for c in QDRANT_CLIENT.get_collections().collections]
    create_collection_if_not_exists(collection_name)

    n_items = len(items)
    print(f"Total items to process: {n_items}")
    for idx in range(0, n_items, batchsize):
        batch = items[idx : idx + batchsize]
        print(f"Processing batch {idx // batchsize + 1} of {((n_items - 1) // batchsize) + 1}.")
        _embed_batch(batch)

    n_remaining = len(get_un_embedded(items))
    print(f"Finished generating embeddings. {n_remaining} items remaining without embeddings.")


@beartype
def re_embed_cards(batchsize: int = 64, max_workers: int = 5) -> None:
    """Re-embed all cards into the Qdrant card collection.

    Args:
        batchsize: Number of cards per upsert batch.
        max_workers: Maximum concurrent embedding threads.
    """
    cards = list(Card.objects.prefetch_related("printings").all())
    _re_embed_items(
        items=cards,
        item_to_point=card_to_qm_pointstruct,
        item_label=lambda c: c.name,
        collection_name=CARD_COLLECTION_NAME,
        batchsize=batchsize,
        max_workers=max_workers,
    )


@beartype
def re_embed_memories(batchsize: int = 64, max_workers: int = 5) -> None:
    """Re-embed all memories into the Qdrant memory collection.

    Args:
        batchsize: Number of memories per upsert batch.
        max_workers: Maximum concurrent embedding threads.
    """

    def memory_to_point(memory: Memory) -> qm.PointStruct:
        """Convert a Memory instance to a Qdrant PointStruct.

        Args:
            memory: The memory to embed.

        Returns:
            A Qdrant PointStruct with a dense embedding and associated payload.
        """
        embedding = dense_embed(memory.text)
        str_related_card_uuids = sorted(str(card.id) for card in memory.related_cards.all())
        return qm.PointStruct(
            id=str(memory.id),
            vector={'dense': embedding},
            payload={
                "name": memory.name,
                "text": memory.text,
                "related_card_uuids": str_related_card_uuids,
                "created_at": memory.created_at.isoformat(),
            },
        )

    memories = list(Memory.objects.prefetch_related("related_cards").all())
    _re_embed_items(
        items=memories,
        item_to_point=memory_to_point,
        item_label=lambda m: m.name,
        collection_name=MEMORY_COLLECTION_NAME,
        batchsize=batchsize,
        max_workers=max_workers,
    )


@beartype
def re_embed_themes(batchsize: int = 64, max_workers: int = 5) -> None:
    """Re-embed all daily deck themes into the Qdrant theme collection.

    Args:
        batchsize: Number of themes per upsert batch.
        max_workers: Maximum concurrent embedding threads.
    """

    def theme_to_point(theme: DailyDeckTheme) -> qm.PointStruct:
        """Convert a DailyDeckTheme to a Qdrant PointStruct.

        Args:
            theme: The theme to embed.

        Returns:
            A Qdrant PointStruct with a dense embedding and associated payload.
        """
        embedding = dense_embed(theme.theme)
        return qm.PointStruct(
            id=str(theme.id),
            vector={'dense': embedding},
            payload={
                "description": theme.theme,
                "date": theme.date.isoformat(),
            },
        )

    themes = list(DailyDeckTheme.objects.all())
    _re_embed_items(
        items=themes,
        item_to_point=theme_to_point,
        item_label=lambda t: t.theme,
        collection_name=THEME_COLLECTION_NAME,
        batchsize=batchsize,
        max_workers=max_workers,
    )


class Command(BaseCommand):
    help = 'Run re-embedding of qdrant items.'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--item-type',
            type=str,
            choices=['cards', 'memories', 'themes'],
            help='Type of items to re-embed',
            required=True,
        )
        parser.add_argument('--batchsize', type=int, default=64, help='Upsert batch size (default: 64)')
        parser.add_argument('--max-workers', type=int, default=50, help='Maximum number of concurrent workers')

    def handle(self, *args: Any, **options: Any) -> None:
        if options['item_type'] == 'cards':
            re_embed_cards(
                batchsize=options.get('batchsize', 64),
                max_workers=options.get('max_workers', 50),
            )
        elif options['item_type'] == 'memories':
            re_embed_memories(
                batchsize=options.get('batchsize', 64),
                max_workers=options.get('max_workers', 50),
            )
        elif options['item_type'] == 'themes':
            re_embed_themes(
                batchsize=options.get('batchsize', 64),
                max_workers=options.get('max_workers', 50),
            )
        else:
            print(f"Unknown item type: {options['item_type']}")
