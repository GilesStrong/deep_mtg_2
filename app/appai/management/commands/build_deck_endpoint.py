import argparse
from time import sleep
from typing import Any

import httpx
from appcards.models.deck import Deck
from django.core.management.base import BaseCommand


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
        with httpx.Client() as client:
            response = client.post(
                'http://localhost:8001/api/app/ai/deck/',
                json={'prompt': theme, 'deck_id': deck_id} if deck_id else {'prompt': theme},
            )

        if response.status_code != 201:
            self.stderr.write(self.style.ERROR(f"Failed to build deck: {response.text}"))
            return

        task_data = response.json()
        task_id = task_data['task_id']
        status_url = task_data['status_url']
        deck_id = task_data['deck_id']
        self.stdout.write(self.style.SUCCESS(f"Deck build task created with ID: {task_id}"))
        self.stdout.write(f"Deck ID: {deck_id}")
        self.stdout.write(f"Checking status at: {status_url}")

        while True:
            status_response = client.get(f'http://localhost:8001{status_url}')
            if status_response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"Failed to check status: {status_response.text}"))
                return
            status_data = status_response.json()
            status = status_data['status']
            deck_id = status_data['deck_id']
            self.stdout.write(f"Current status: {status}")
            if status == 'COMPLETED':
                break
            elif status == 'FAILED':
                self.stderr.write(self.style.ERROR("Deck building task failed"))
                return
            else:
                self.stdout.write("Waiting for task to complete...")
                sleep(5)

        deck = Deck.objects.prefetch_related('deckcard_set__card').get(id=deck_id)
        print(f"Deck name: {deck.name}")
        print("Cards in deck:")
        for deck_card in deck.deckcard_set.all():
            print(f" - {deck_card.quantity}x {deck_card.card.name}")
