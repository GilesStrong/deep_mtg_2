import argparse
import json
import re
from pathlib import Path
from typing import Any

from appcards.constants.extraction import EXTRACTION_SCHEMA
from appcards.models.card import Card
from beartype import beartype
from django.core.management.base import BaseCommand
from django.db import transaction
from langchain_community.document_loaders import JSONLoader
from tqdm import tqdm

DIGIT_IN_BRACES = re.compile(r"\{(\d+)\}")


@beartype
def extract_digit(s: str) -> int | None:
    m = DIGIT_IN_BRACES.search(s)
    return int(m.group(1)) if m else None


def add_cards(card_json_path: Path) -> None:
    loader = JSONLoader(card_json_path, EXTRACTION_SCHEMA, text_content=False)
    extracted_cards = loader.load()
    seen_card_names = set(Card.objects.values_list('name', flat=True))
    new_cards: list[Card] = []

    for card_data in tqdm(extracted_cards, desc="Processing cards"):
        card_dict = json.loads(card_data.page_content)

        name = card_dict['name']
        if name is None or name in seen_card_names:
            continue

        text = card_dict['text'] or ""
        subtypes = card_dict['subtypes'] or []
        supertypes = card_dict['supertypes'] or []
        keywords = card_dict['keywords'] or []
        power = card_dict['power']
        toughness = card_dict['toughness']
        keywords = card_dict['keywords'] or []
        colors = card_dict['colors'] or []
        types = card_dict['types'] or []
        rarity = card_dict['rarity'] or "COMMON"
        converted_mana_cost = card_dict['convertedManaCost'] or 0

        if card_dict['manaCost'] is None:
            mana_cost_red = 0
            mana_cost_blue = 0
            mana_cost_green = 0
            mana_cost_white = 0
            mana_cost_black = 0
            mana_cost_colorless = 0
        else:
            mana_cost_str = card_dict['manaCost']
            mana_cost_red = mana_cost_str.count('R')
            mana_cost_blue = mana_cost_str.count('U')
            mana_cost_green = mana_cost_str.count('G')
            mana_cost_white = mana_cost_str.count('W')
            mana_cost_black = mana_cost_str.count('B')
            mana_cost_colorless = extract_digit(mana_cost_str) or 0

        card = Card(
            name=name,
            text=text,
            subtypes=subtypes,
            supertypes=supertypes,
            power=power,
            toughness=toughness,
            mana_cost_red=mana_cost_red,
            mana_cost_blue=mana_cost_blue,
            mana_cost_green=mana_cost_green,
            mana_cost_white=mana_cost_white,
            mana_cost_black=mana_cost_black,
            mana_cost_colorless=mana_cost_colorless,
            converted_mana_cost=converted_mana_cost,
            colors=colors,
            types=types,
            rarity=rarity,
            keywords=keywords,
        )
        new_cards.append(card)
        seen_card_names.add(name)

    print(f"Adding {len(new_cards)} new cards to the database.")

    with transaction.atomic():
        Card.objects.bulk_create(new_cards, ignore_conflicts=True)

    print("Card addition complete.")
    print(f"Total cards in database: {Card.objects.count()}")


class Command(BaseCommand):
    help = 'Add multiple cards to the database'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--card-json-path', type=str, help='Path to the JSON file containing card data')

    def handle(self, *args: Any, **options: Any) -> None:
        add_cards(Path(options['card_json_path']))
