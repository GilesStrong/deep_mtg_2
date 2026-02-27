import argparse
import json
import re
from pathlib import Path
from typing import Any

from appcore.modules.beartype import beartype
from django.core.management.base import BaseCommand
from django.db import transaction
from langchain_community.document_loaders import JSONLoader
from tqdm import tqdm

from appcards.constants.extraction import EXTRACTION_SCHEMA
from appcards.models.card import Card
from appcards.models.printing import Printing

DIGIT_IN_BRACES = re.compile(r"\{(\d+)\}")


@beartype
def extract_digit(s: str) -> int | None:
    m = DIGIT_IN_BRACES.search(s)
    return int(m.group(1)) if m else None


def add_cards(card_json_path: Path) -> None:
    loader = JSONLoader(card_json_path, EXTRACTION_SCHEMA, text_content=False)
    extracted_cards = loader.load()

    cards_by_name: dict[str, Card] = {}
    printing_keys: set[tuple[str, str]] = set()

    for card_data in tqdm(extracted_cards, desc="Processing cards"):
        card_dict = json.loads(card_data.page_content)

        name = card_dict.get("name")
        set_code = card_dict.get("setCode")
        if not name or not set_code:
            raise ValueError(f"Card name or set code is missing: {card_dict}")

        printing_keys.add((name, set_code))

        if name not in cards_by_name:
            mana_cost_str = card_dict.get("manaCost")
            if mana_cost_str is None:
                mana_cost_red = 0
                mana_cost_blue = 0
                mana_cost_green = 0
                mana_cost_white = 0
                mana_cost_black = 0
                mana_cost_colorless = 0
            else:
                mana_cost_red = mana_cost_str.count('R')
                mana_cost_blue = mana_cost_str.count('U')
                mana_cost_green = mana_cost_str.count('G')
                mana_cost_white = mana_cost_str.count('W')
                mana_cost_black = mana_cost_str.count('B')
                mana_cost_colorless = extract_digit(mana_cost_str) or 0

            card = Card(
                name=name,
                text=card_dict.get("text") or "",
                subtypes=card_dict.get("subtypes") or [],
                supertypes=card_dict.get("supertypes") or [],
                power=card_dict.get("power"),
                toughness=card_dict.get("toughness"),
                mana_cost_red=mana_cost_red,
                mana_cost_blue=mana_cost_blue,
                mana_cost_green=mana_cost_green,
                mana_cost_white=mana_cost_white,
                mana_cost_black=mana_cost_black,
                mana_cost_colorless=mana_cost_colorless,
                converted_mana_cost=card_dict.get("convertedManaCost") or 0,
                colors=card_dict.get("colors") or [],
                types=card_dict.get("types") or [],
                rarity=card_dict.get("rarity") or "common",
                keywords=card_dict.get("keywords") or [],
            )
            cards_by_name[name] = card

    new_cards = list(cards_by_name.values())
    names = list(cards_by_name.keys())

    print(f"Upserting {len(new_cards)} unique card names.")
    print(f"Upserting {len(printing_keys)} unique printings (name,set).")

    with transaction.atomic():
        Card.objects.bulk_create(new_cards, ignore_conflicts=True, batch_size=5000)

        # Add printings
        card_lookup = dict(Card.objects.filter(name__in=names).values_list("name", "id"))
        new_printings = [Printing(card_id=card_lookup[name], set_code=set_code) for (name, set_code) in printing_keys]
        Printing.objects.bulk_create(new_printings, ignore_conflicts=True, batch_size=5000)

    print("Card addition complete.")
    print(f"Total cards in database: {Card.objects.count()}")
    print(f"Total printings in database: {Printing.objects.count()}")


class Command(BaseCommand):
    help = 'Add multiple cards to the database'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--card-json-path', type=str, required=True, help='Path to the JSON file containing card data'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        add_cards(Path(options['card_json_path']))
