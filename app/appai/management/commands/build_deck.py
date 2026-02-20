import argparse
import asyncio
from typing import Any
from uuid import UUID

from appcards.models.deck import Deck
from django.core.management.base import BaseCommand

from appai.modules.construct_deck import construct_deck


class Command(BaseCommand):
    help = 'Playground for building a deck using the agent'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--theme', type=str, required=True, help='Theme or description for the deck to be constructed'
        )
        parser.add_argument('--deck-id', type=str, required=False, help='Optional existing deck ID to build upon')

    def handle(self, *args: Any, **options: Any) -> None:
        theme = options['theme']
        deck_id = options['deck_id']
        if deck_id:
            try:
                deck_id = UUID(deck_id)
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid deck ID format: {deck_id}"))
                return
        else:
            deck_id = None

        response = asyncio.run(construct_deck(theme, deck_id=deck_id))
        print(f"Constructed deck: {response}")

        deck = Deck.objects.prefetch_related('deckcard_set__card').get(id=response.deck_id)
        print(f"Deck name: {deck.name}")
        print("Cards in deck:")
        for deck_card in deck.deckcard_set.all():
            print(f" - {deck_card.quantity}x {deck_card.card.name}")
