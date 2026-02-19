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
            print(f"Retrieved card ID: {p.id}, score: {p.score}, payload name: {p.payload['name']}")
