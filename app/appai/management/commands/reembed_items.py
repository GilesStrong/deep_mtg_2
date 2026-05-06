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
from typing import Any

from appcards.constants.storage import CARD_COLLECTION_NAME
from appcards.models.card import Card
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


@beartype
def re_embed_cards(batchsize: int = 64, max_workers: int = 5) -> None:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def embed_card(card: Card, semaphore: Semaphore) -> qm.PointStruct:
        with semaphore:
            point = card_to_qm_pointstruct(card)
            print(f"✓ Generated embedding for: {card.name}")
            return point

    def _embed_cards_batch(batch: list[Card], max_workers: int) -> None:
        semaphore = Semaphore(max_workers)
        embedding_results: list[qm.PointStruct] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(embed_card, card, semaphore) for card in batch]

            for future in as_completed(futures):
                try:
                    embedding_results.append(future.result())
                except Exception as e:
                    print(f"✗ Failed to generate embedding: {e}")
        upsert_documents(collection_name=CARD_COLLECTION_NAME, points=embedding_results)

    def get_un_embedded_cards(cards: list[Card]) -> list[Card]:
        existing_points = QDRANT_CLIENT.retrieve(
            collection_name=CARD_COLLECTION_NAME,
            ids=[str(card.id) for card in cards],
            with_payload=True,
            with_vectors=False,
        )

        existing_ids = set(str(p.id) for p in existing_points)
        return [card for card in cards if str(card.id) not in existing_ids]

    batchsize = max(1, batchsize)
    QDRANT_CLIENT.delete_collection(collection_name=CARD_COLLECTION_NAME)
    assert CARD_COLLECTION_NAME not in [c.name for c in QDRANT_CLIENT.get_collections().collections]
    create_collection_if_not_exists(CARD_COLLECTION_NAME)

    cards = list(Card.objects.prefetch_related("printings").all())
    n_cards = len(cards)
    for idx in range(0, n_cards, batchsize):
        batch = cards[idx : idx + batchsize]
        print(f"Processing batch {idx // batchsize + 1} of {((n_cards - 1) // batchsize) + 1}.")
        _embed_cards_batch(batch, max_workers)

    n_remaining = len(get_un_embedded_cards(cards))
    print(f"Finished generating embeddings. {n_remaining} cards remaining without embeddings.")


@beartype
def re_embed_memories(batchsize: int = 64, max_workers: int = 5) -> None:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def embed_memory(memory: Memory, semaphore: Semaphore) -> qm.PointStruct:
        with semaphore:
            embedding = dense_embed(memory.text)
            str_related_card_uuids = sorted((str(card.id) for card in memory.related_cards.all()))

            point = qm.PointStruct(
                id=str(memory.id),
                vector={'dense': embedding},
                payload={
                    "name": memory.name,
                    "text": memory.text,
                    "related_card_uuids": str_related_card_uuids,
                    "created_at": memory.created_at.isoformat(),
                },
            )
            print(f"✓ Generated embedding for: {memory.name}")
            return point

    def _embed_memory_batch(batch: list[Memory], max_workers: int) -> None:
        semaphore = Semaphore(max_workers)
        embedding_results: list[qm.PointStruct] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(embed_memory, memory, semaphore) for memory in batch]

            for future in as_completed(futures):
                try:
                    embedding_results.append(future.result())
                except Exception as e:
                    print(f"✗ Failed to generate embedding: {e}")
        upsert_documents(collection_name=MEMORY_COLLECTION_NAME, points=embedding_results)

    def get_un_embedded_memories(memories: list[Memory]) -> list[Memory]:
        existing_points = QDRANT_CLIENT.retrieve(
            collection_name=MEMORY_COLLECTION_NAME,
            ids=[str(memory.id) for memory in memories],
            with_payload=True,
            with_vectors=False,
        )

        existing_ids = set(str(p.id) for p in existing_points)
        return [memory for memory in memories if str(memory.id) not in existing_ids]

    batchsize = max(1, batchsize)
    QDRANT_CLIENT.delete_collection(collection_name=MEMORY_COLLECTION_NAME)
    assert MEMORY_COLLECTION_NAME not in [c.name for c in QDRANT_CLIENT.get_collections().collections]
    create_collection_if_not_exists(MEMORY_COLLECTION_NAME)

    memories = list(Memory.objects.prefetch_related("related_cards").all())
    n_memories = len(memories)
    for idx in range(0, n_memories, batchsize):
        batch = memories[idx : idx + batchsize]
        print(f"Processing batch {idx // batchsize + 1} of {((n_memories - 1) // batchsize) + 1}.")
        _embed_memory_batch(batch, max_workers)

    n_remaining = len(get_un_embedded_memories(memories))
    print(f"Finished generating embeddings. {n_remaining} memories remaining without embeddings.")


class Command(BaseCommand):
    help = 'Run re-embedding of qdrant items.'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--item-type',
            type=str,
            choices=['cards', 'memories'],
            help='Type of items to re-embed',
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
