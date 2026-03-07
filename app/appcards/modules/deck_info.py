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

from appcore.modules.beartype import beartype

from appcards.constants.decks import COLOR_IDENTITY_TO_COLORS, GROUPED_DECK_CLASSIFICATIONS
from appcards.models.deck import Deck


@beartype
def get_colors_from_deck(deck: Deck) -> set[str]:
    """
    Extracts the color identity of a deck based on the colors of the cards it contains.

    Args:
        deck (Deck): The Deck instance for which to determine the color identity.

    Returns:
        set[str]: A set of color names representing the deck's color identity.
    """

    if deck.tags is not None:
        color_identities: set[str] = set()
        for color_identity in GROUPED_DECK_CLASSIFICATIONS['ColorIdentity'].keys():
            if color_identity in deck.tags:
                color_identities.add(color_identity)
        if len(color_identities) > 0:
            colors: set[str] = set()
            for ci in color_identities:
                colors.update(COLOR_IDENTITY_TO_COLORS.get(ci, []))
            return colors

    card_colors = set()
    for deck_card in deck.deckcard_set.select_related('card').all():
        card_colors.update(deck_card.card.colors)
    return card_colors
