import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from typing import Any, Optional

from beartype import beartype
from django.core.management.base import BaseCommand
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from appcards.models import Card
from appcards.modules.card_info import card_to_info
from appcards.modules.summarise_card import summarise_card


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception),
)
def generate_card_summary(card: Card, semaphore: Semaphore) -> None:
    with semaphore:
        info = card_to_info(card)
        summary = summarise_card(info)
        card.llm_summary = summary
        card.save(update_fields=['llm_summary'])
        print(f"✓ Generated summary for: {card.name}")


@beartype
def generate_card_summaries(n_max_summaries: Optional[int], max_workers: int = 5) -> None:
    cards = Card.objects.filter(llm_summary__isnull=True).prefetch_related("printings")
    print(f"Generating summaries for {cards.count()} cards")
    if n_max_summaries is not None:
        if n_max_summaries <= 0:
            raise ValueError("n_max_summaries must be positive")
        print(f"Limiting to {n_max_summaries} summaries")
        cards = cards[:n_max_summaries]

    semaphore = Semaphore(max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generate_card_summary, card, semaphore) for card in cards]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"✗ Failed to generate summary: {e}")

    n_remaining = Card.objects.filter(llm_summary__isnull=True).count()
    print(f"Finished generating summaries. {n_remaining} cards remaining without summaries.")


class Command(BaseCommand):
    help = 'Generate LLM summaries for cards without summaries'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--n-max-summaries', type=int, required=False, help='Maximum number of summaries to generate'
        )
        parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of concurrent workers')

    def handle(self, *args: Any, **options: Any) -> None:
        generate_card_summaries(
            n_max_summaries=options.get('n_max_summaries'), max_workers=options.get('max_workers', 5)
        )
