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

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appuser.models import User
from django.test import TestCase
from django.utils import timezone
from ninja.errors import HttpError

from appcards.constants.cards import HIERARCHICAL_TAGS, PRIMARY_TAG_DESCRIPTIONS
from appcards.models.card import Card, Rarity
from appcards.models.deck import DailyDeckTheme, Deck, DeckCard
from appcards.models.printing import Printing
from appcards.routes.card import get_card, list_set_codes, list_tags
from appcards.routes.deck import delete_deck, get_daily_theme, get_deck, get_summary_deck, list_decks, update_deck
from appcards.serializers.deck import UpdateDeckIn

_CARD_MODULE = "appcards.routes.card"


class CardRoutesTests(TestCase):
    """Tests for appcards card routes."""

    def test_list_tags_returns_hierarchical_mapping_with_used_tags(self):
        """
        GIVEN cards with overlapping tag lists
        WHEN list_tags is called
        THEN it returns all primary tags with only used tags populated
        """
        Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON, tags=["Control", "Cantrip"])
        Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON, tags=["Aggro", "Control"])
        Card.objects.create(name="Llanowar Elves", text="Add G.", rarity=Rarity.COMMON, tags=["Ramp"])

        result = list_tags(SimpleNamespace())

        self.assertEqual(result.tags["CardAdvantage"], {"Cantrip": HIERARCHICAL_TAGS["CardAdvantage"]["Cantrip"]})
        self.assertEqual(
            result.tags,
            {
                primary_tag: {
                    **(
                        {primary_tag: PRIMARY_TAG_DESCRIPTIONS[primary_tag]}
                        if primary_tag in {"Aggro", "Control", "Ramp"}
                        else {}
                    ),
                    **(
                        {"Cantrip": HIERARCHICAL_TAGS["CardAdvantage"]["Cantrip"]}
                        if primary_tag == "CardAdvantage"
                        else {}
                    ),
                }
                for primary_tag in HIERARCHICAL_TAGS
            },
        )

    def test_list_tags_ignores_non_string_and_blank_values(self):
        """
        GIVEN cards with null, non-string, and blank tag values
        WHEN list_tags is called
        THEN it ignores invalid values and still returns valid hierarchical tags
        """
        Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON, tags=["Control", "", "  ", None])
        Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON, tags=["Aggro", 123])

        result = list_tags(SimpleNamespace())

        self.assertEqual(result.tags["Control"], {"Control": PRIMARY_TAG_DESCRIPTIONS["Control"]})
        self.assertEqual(result.tags["Aggro"], {"Aggro": PRIMARY_TAG_DESCRIPTIONS["Aggro"]})

    def test_list_set_codes_returns_distinct_sorted_values(self):
        """
        GIVEN multiple printings including duplicate set codes
        WHEN list_set_codes is called
        THEN it returns distinct set codes in ascending order
        """
        card = Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON)
        Printing.objects.create(card=card, set_code="M20")
        Printing.objects.create(card=card, set_code="FDN")

        card2 = Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON)
        Printing.objects.create(card=card2, set_code="FDN")

        result = list_set_codes(SimpleNamespace())

        self.assertEqual(result.set_codes, ["FDN", "M20"])

    @patch(f"{_CARD_MODULE}.card_to_info")
    def test_get_card_returns_card_info_for_path_param_card(self, mock_card_to_info):
        """
        GIVEN path params that already resolve to a card instance
        WHEN get_card is called
        THEN it delegates to card_to_info and returns that value
        """
        card = Card.objects.create(name="Consider", text="Draw then mill.", rarity=Rarity.COMMON)
        expected = SimpleNamespace(name="Consider")
        mock_card_to_info.return_value = expected

        result = get_card(SimpleNamespace(), SimpleNamespace(card=card))

        self.assertEqual(result, expected)


class DeckRoutesTests(TestCase):
    """Tests for appcards deck routes."""

    @patch("appcards.routes.deck.get_user_from_request")
    def test_list_decks_uses_latest_build_per_deck(self, mock_get_user):
        """
        GIVEN multiple build tasks per deck with different update times
        WHEN list_decks is called
        THEN each deck summary uses the most recently updated task status and task_id
        """
        user = User.objects.create(google_id="owner-list-gid", verified=True)
        mock_get_user.return_value = user

        first_deck = Deck.objects.create(name="Deck One", user=user)
        second_deck = Deck.objects.create(name="Deck Two", user=user)

        now = timezone.now()

        old_first = DeckBuildTask.objects.create(deck=first_deck, status=DeckBuildStatus.PENDING)
        new_first = DeckBuildTask.objects.create(deck=first_deck, status=DeckBuildStatus.COMPLETED)
        only_second = DeckBuildTask.objects.create(deck=second_deck, status=DeckBuildStatus.FAILED)

        DeckBuildTask.objects.filter(id=old_first.id).update(updated_at=now - timedelta(hours=3))
        DeckBuildTask.objects.filter(id=new_first.id).update(updated_at=now - timedelta(hours=1))
        DeckBuildTask.objects.filter(id=only_second.id).update(updated_at=now - timedelta(hours=2))

        result = list_decks(SimpleNamespace(auth=user))

        by_id = {deck_summary.id: deck_summary for deck_summary in result}

        self.assertEqual(by_id[first_deck.id].generation_status, DeckBuildStatus.COMPLETED)
        self.assertEqual(by_id[first_deck.id].generation_task_id, new_first.id)
        self.assertEqual(by_id[second_deck.id].generation_status, DeckBuildStatus.FAILED)
        self.assertEqual(by_id[second_deck.id].generation_task_id, only_second.id)

    def test_get_summary_deck_includes_tags(self):
        """
        GIVEN an owned deck with tags
        WHEN get_summary_deck is called
        THEN the response includes the deck tags
        """
        user = User.objects.create(google_id="owner-tags-gid", verified=True)
        deck = Deck.objects.create(name="Tagged Deck", user=user, tags=["Aggro", "Burn"])

        response = get_summary_deck(SimpleNamespace(auth=user), SimpleNamespace(deck=deck))

        self.assertCountEqual(response.tags, ["Aggro", "Burn"])

    def test_get_summary_deck_blocks_non_owner(self):
        """
        GIVEN a deck owned by another user
        WHEN get_summary_deck is called by the current user
        THEN it raises HttpError 403
        """
        owner = User.objects.create(google_id="owner-gid", verified=True)
        other = User.objects.create(google_id="other-gid", verified=True)
        deck = Deck.objects.create(name="Owner Deck", user=owner)

        request = SimpleNamespace(auth=other)
        with self.assertRaises(HttpError) as ctx:
            get_summary_deck(request, SimpleNamespace(deck=deck))

        self.assertEqual(ctx.exception.status_code, 403)

    def test_delete_deck_allows_owner(self):
        """
        GIVEN a deck owned by the authenticated user
        WHEN delete_deck is called
        THEN the deck is deleted and None is returned
        """
        user = User.objects.create(google_id="delete-gid", verified=True)
        deck = Deck.objects.create(name="Delete Me", user=user)

        result = delete_deck(SimpleNamespace(auth=user), SimpleNamespace(deck=deck))

        self.assertIsNone(result)
        self.assertFalse(Deck.objects.filter(id=deck.id).exists())

    def test_delete_deck_blocks_when_latest_build_is_pollable(self):
        """
        GIVEN a deck with an active pollable build task
        WHEN delete_deck is called
        THEN it raises HttpError 409 and does not delete the deck
        """
        user = User.objects.create(google_id="delete-blocked-gid", verified=True)
        deck = Deck.objects.create(name="Cannot Delete Yet", user=user)
        DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.IN_PROGRESS)

        with self.assertRaises(HttpError) as ctx:
            delete_deck(SimpleNamespace(auth=user), SimpleNamespace(deck=deck))

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertTrue(Deck.objects.filter(id=deck.id).exists())

    def test_get_daily_theme_returns_fallback_when_no_themes_exist(self):
        """
        GIVEN no DailyDeckTheme records exist
        WHEN get_daily_theme is called
        THEN it returns the hard-coded fallback theme string
        """
        result = get_daily_theme(SimpleNamespace())

        self.assertEqual(
            result,
            "Blue-White Control: counterspells, card draw, and versatile answers to threats, with a focus on controlling the game and winning in the late game.",
        )

    def test_get_daily_theme_returns_latest_persisted_theme(self):
        """
        GIVEN multiple DailyDeckTheme records across days
        WHEN get_daily_theme is called
        THEN it returns the most recent theme by date
        """
        older = DailyDeckTheme.objects.create(theme="Older theme")
        newer = DailyDeckTheme.objects.create(theme="Newest theme")
        DailyDeckTheme.objects.filter(id=older.id).update(date=date.today() - timedelta(days=1))
        DailyDeckTheme.objects.filter(id=newer.id).update(date=date.today())

        result = get_daily_theme(SimpleNamespace())

        self.assertEqual(result, "Newest theme")

    def test_get_deck_includes_possible_replacements(self):
        """
        GIVEN a deck card with replacement cards
        WHEN get_deck is called
        THEN possible_replacements contains serialized replacement card infos
        """
        user = User.objects.create(google_id="deck-replacements-gid", verified=True)
        deck = Deck.objects.create(name="Replacement Deck", user=user)
        main_card = Card.objects.create(name="Lightning Bolt", text="Deal 3 damage.", rarity=Rarity.COMMON)
        replacement_1 = Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON)
        replacement_2 = Card.objects.create(name="Burst Lightning", text="Deal 2 damage.", rarity=Rarity.COMMON)

        deck_card = DeckCard.objects.create(deck=deck, card=main_card, quantity=2)
        deck_card.replacement_cards.add(replacement_1, replacement_2)

        response = get_deck(SimpleNamespace(auth=user), SimpleNamespace(deck=deck))

        self.assertEqual(len(response.cards), 1)
        self.assertEqual(response.cards[0].card_info.name, "Lightning Bolt")
        self.assertCountEqual(
            [replacement.name for replacement in response.cards[0].possible_replacements],
            ["Shock", "Burst Lightning"],
        )

    def test_update_deck_includes_possible_replacements(self):
        """
        GIVEN an owned deck card with replacement cards
        WHEN update_deck updates metadata
        THEN response cards include possible_replacements for each deck card
        """
        user = User.objects.create(google_id="deck-update-replacements-gid", verified=True)
        deck = Deck.objects.create(name="Before Update", user=user)
        main_card = Card.objects.create(name="Counterspell", text="Counter target spell.", rarity=Rarity.UNCOMMON)
        replacement = Card.objects.create(name="Negate", text="Counter target noncreature spell.", rarity=Rarity.COMMON)

        deck_card = DeckCard.objects.create(deck=deck, card=main_card, quantity=3)
        deck_card.replacement_cards.add(replacement)

        response = update_deck(
            SimpleNamespace(auth=user),
            SimpleNamespace(deck=deck),
            UpdateDeckIn(name="After Update"),
        )

        self.assertEqual(response.name, "After Update")
        self.assertEqual(len(response.cards), 1)
        self.assertEqual(response.cards[0].card_info.name, "Counterspell")
        self.assertEqual([candidate.name for candidate in response.cards[0].possible_replacements], ["Negate"])

    def test_update_deck_blocks_when_latest_build_is_pollable(self):
        """
        GIVEN an owned deck with an active pollable build status
        WHEN update_deck is called
        THEN it raises HttpError 409 to prevent editing during generation
        """
        user = User.objects.create(google_id="deck-update-blocked-gid", verified=True)
        deck = Deck.objects.create(name="In Progress Deck", user=user)
        DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.BUILDING_DECK)

        with self.assertRaises(HttpError) as ctx:
            update_deck(
                SimpleNamespace(auth=user),
                SimpleNamespace(deck=deck),
                UpdateDeckIn(name="Should Not Save"),
            )

        self.assertEqual(ctx.exception.status_code, 409)
