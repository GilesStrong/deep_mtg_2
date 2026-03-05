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
