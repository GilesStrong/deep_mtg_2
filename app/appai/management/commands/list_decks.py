from typing import Any

import httpx
from django.core.management.base import BaseCommand

BASE_URL = 'http://0.0.0.0:8001'


class Command(BaseCommand):
    help = 'Playground for building a deck using the agent'

    def handle(self, *args: Any, **options: Any) -> None:
        with httpx.Client() as client:
            status_response = client.get(f'{BASE_URL}/api/app/cards/deck/', timeout=10.0)
            if status_response.status_code != 200:
                self.stderr.write(self.style.ERROR(f"Failed to retrieve decks: {status_response.text}"))
                return
            status_data = status_response.json()
            print(status_data)
