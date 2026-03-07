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
import asyncio
from typing import Any

from appai.services.agents.filter_constructor import filter_constructor
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Query
from django.core.management.base import BaseCommand

from appcards.constants.storage import CARD_COLLECTION_NAME


class Command(BaseCommand):
    help = 'Playground for testing retrieval of cards with filters constructed from natural language queries'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--query', type=str, required=True, help='Search query to filter cards')
        parser.add_argument('--limit', type=int, default=10, help='Retrieval limit (default: 10)')

    def handle(self, *args: Any, **options: Any) -> None:
        query = options['query']
        limit = options['limit']

        query_filter = asyncio.run(filter_constructor(query))
        print(f"Constructed filter: {query_filter}")

        points = run_query_from_dsl(
            dsl_query=Query(collection_name=CARD_COLLECTION_NAME, query_string=query, filter=query_filter, limit=limit),
        )

        for p in points:
            print(f"Retrieved card ID: {p.id}, score: {p.score}, payload: {p.payload}")
