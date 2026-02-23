from appai.models.deck_build import DeckBuildTask
from django.http import HttpRequest
from ninja import Path, Router

from appcards.models.deck import Deck, DeckCard
from appcards.modules.card_info import card_to_info
from appcards.serializers.deck import GetDeckIn, GetFullDeckOut, GetSummaryDeckOut

router = Router(tags=['decks'])


def _get_latest_build(deck_id: str) -> DeckBuildTask | None:
    return DeckBuildTask.objects.filter(deck_id=deck_id).order_by('-updated_at').first()


@router.get(
    '/',
    summary='List deck summaries',
    description='Retrieve summaries for all decks, ordered by most recently updated.',
    response={200: list[GetSummaryDeckOut]},
    operation_id='list_decks',
)
def list_decks(request: HttpRequest) -> list[GetSummaryDeckOut]:
    decks = []

    for deck in Deck.objects.order_by('-updated_at'):
        latest_build = _get_latest_build(str(deck.id))
        decks.append(
            GetSummaryDeckOut(
                id=deck.id,
                name=deck.name,
                short_summary=deck.short_llm_summary,
                set_codes=deck.set_codes,
                date_updated=deck.updated_at.isoformat(),
                generation_status=latest_build.status if latest_build else None,
                generation_task_id=latest_build.id if latest_build else None,
            )
        )

    return decks


@router.get(
    '/{deck_id}/',
    summary='Get deck details',
    description='Retrieve the details of a deck by its ID.',
    response={200: GetSummaryDeckOut},
    operation_id='get_deck',
)
def get_summary_deck(request: HttpRequest, path_params: Path[GetDeckIn]) -> GetSummaryDeckOut:
    """
    Retrieve the summary details of a deck by its ID.

    This endpoint allows you to fetch the details of a specific deck using its unique identifier.
    The response will include information about the deck, such as its name, short summary, and the set codes it contains.
    """

    deck = path_params.deck
    latest_build = _get_latest_build(str(deck.id))
    return GetSummaryDeckOut(
        id=deck.id,
        name=deck.name,
        short_summary=deck.short_llm_summary,
        set_codes=deck.set_codes,
        date_updated=deck.updated_at.isoformat(),
        generation_status=latest_build.status if latest_build else None,
        generation_task_id=latest_build.id if latest_build else None,
    )


@router.get(
    '/{deck_id}/full/',
    summary='Get full deck details',
    description='Retrieve the full details of a deck by its ID.',
    response={200: GetFullDeckOut},
    operation_id='get_full_deck',
)
def get_deck(request: HttpRequest, path_params: Path[GetDeckIn]) -> GetFullDeckOut:
    """
    Retrieve the full details of a deck by its ID.

    This endpoint allows you to fetch the details of a specific deck using its unique identifier.
    The response will include information about the deck, such as its name, full description, and the cards it contains.
    """
    deck = path_params.deck
    deck_cards = list(DeckCard.objects.filter(deck_id=deck.id).select_related('card'))
    card_infos = [(deck_card.quantity, card_to_info(deck_card.card)) for deck_card in deck_cards]

    return GetFullDeckOut(
        id=deck.id,
        name=deck.name,
        short_summary=deck.short_llm_summary,
        full_summary=deck.llm_summary,
        set_codes=deck.set_codes,
        date_updated=deck.updated_at.isoformat(),
        cards=card_infos,
    )
