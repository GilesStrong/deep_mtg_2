import argparse
import asyncio
from typing import Any

from appcards.models.deck import Deck
from django.core.management.base import BaseCommand

from appai.modules.construct_deck import construct_deck


class Command(BaseCommand):
    help = 'Playground for building a deck using the agent'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--theme', type=str, required=True, help='Theme or description for the deck to be constructed'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        theme = options['theme']

        response = asyncio.run(construct_deck(theme))
        print(f"Constructed deck: {response}")

        deck = Deck.objects.prefetch_related('deckcard_set__card').get(id=response.deck_id)
        print(f"Deck name: {deck.name}")
        print("Cards in deck:")
        for deck_card in deck.deckcard_set.all():
            print(f" - {deck_card.quantity}x {deck_card.card.name}")
