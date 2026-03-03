from appai.models.deck_build import DeckBuildTask
from appauth.modules.auth import get_user_from_request
from django.http import HttpRequest
from ninja import Path, Router
from ninja.errors import HttpError

from appcards.models.deck import DailyDeckTheme, Deck, DeckCard
from appcards.modules.card_info import card_to_info
from appcards.serializers.deck import GetDeckIn, GetFullDeckOut, GetSummaryDeckOut, UpdateDeckIn

router = Router(tags=['decks'])


def _get_latest_build(deck_id: str) -> DeckBuildTask | None:
    """
    Retrieve the most recent DeckBuildTask for a given deck.

    Args:
        deck_id (str): The unique identifier of the deck.

    Returns:
        DeckBuildTask | None: The latest DeckBuildTask object associated with the
        given deck_id, ordered by the most recently updated. Returns None if no
        DeckBuildTask exists for the given deck_id.
    """
    return DeckBuildTask.objects.filter(deck_id=deck_id).order_by('-updated_at').first()


@router.get(
    '/',
    summary='List deck summaries',
    description='Retrieve summaries for all decks, ordered by most recently updated.',
    response={200: list[GetSummaryDeckOut]},
    operation_id='list_decks',
)
def list_decks(request: HttpRequest) -> list[GetSummaryDeckOut]:
    """
    Retrieve summaries for all decks, ordered by most recently updated.

    Args:
        request (HttpRequest): The incoming HTTP request object.

    Returns:
        list[GetSummaryDeckOut]: A list of deck summary objects
    """
    user = get_user_from_request(request)
    all_decks = list(Deck.objects.filter(user_id=user.id).order_by('-updated_at'))
    deck_ids = [str(deck.id) for deck in all_decks]
    latest_builds = (
        DeckBuildTask.objects.filter(deck_id__in=deck_ids).order_by('deck_id', '-updated_at').distinct('deck_id')
    )
    builds_by_deck_id = {str(build.deck_id): build for build in latest_builds}

    decks = []
    for deck in all_decks:
        latest_build = builds_by_deck_id.get(str(deck.id))
        decks.append(
            GetSummaryDeckOut(
                id=deck.id,
                name=deck.name,
                short_summary=deck.short_llm_summary,
                set_codes=deck.set_codes,
                tags=deck.tags if deck.tags is not None else [],
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
def get_summary_deck(
    request: HttpRequest,
    path_params: Path[GetDeckIn],
) -> GetSummaryDeckOut:
    """
    Retrieve the summary details of a deck by its ID.

    This endpoint allows you to fetch the details of a specific deck using its unique identifier.
    The response will include information about the deck, such as its name, short summary, and the set codes it contains.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        path_params (Path[GetDeckIn]): The path parameters containing the deck ID to retrieve.

    Returns:
        GetSummaryDeckOut: An object containing the summary details of the requested deck.
    """

    user = get_user_from_request(request)
    deck = path_params.deck
    if deck.user.id != user.id:
        raise HttpError(403, "You do not have permission to access this deck")
    latest_build = _get_latest_build(str(deck.id))
    return GetSummaryDeckOut(
        id=deck.id,
        name=deck.name,
        short_summary=deck.short_llm_summary,
        set_codes=deck.set_codes,
        tags=deck.tags if deck.tags is not None else [],
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
def get_deck(
    request: HttpRequest,
    path_params: Path[GetDeckIn],
) -> GetFullDeckOut:
    """
    Retrieve the full details of a deck by its ID.

    This endpoint allows you to fetch the details of a specific deck using its unique identifier.
    The response will include information about the deck, such as its name, full description, and the cards it contains.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        path_params (Path[GetDeckIn]): The path parameters containing the deck ID to retrieve.

    Returns:
        GetFullDeckOut: An object containing the full details of the requested deck, including its cards.
    """
    deck = path_params.deck
    user = get_user_from_request(request)
    if deck.user.id != user.id:
        raise HttpError(403, "You do not have permission to access this deck")

    deck_cards = list(DeckCard.objects.filter(deck_id=deck.id).select_related('card'))
    card_infos = [(deck_card.quantity, card_to_info(deck_card.card)) for deck_card in deck_cards]
    latest_build = _get_latest_build(str(deck.id))
    creation_status = latest_build.status if latest_build else None

    return GetFullDeckOut(
        id=deck.id,
        name=deck.name,
        short_summary=deck.short_llm_summary,
        full_summary=deck.llm_summary,
        set_codes=deck.set_codes,
        tags=deck.tags if deck.tags is not None else [],
        date_updated=deck.updated_at.isoformat(),
        cards=card_infos,
        creation_status=creation_status,
    )


@router.delete(
    '/{deck_id}/',
    summary='Delete a deck',
    description='Delete a deck by its ID.',
    response={204: None},
    operation_id='delete_deck',
)
def delete_deck(
    request: HttpRequest,
    path_params: Path[GetDeckIn],
) -> None:
    """
    Delete a deck by its ID.

    This endpoint allows you to delete a specific deck using its unique identifier.
    You must have permission to delete the deck (i.e. you must be the owner of the deck) in order to successfully delete it. If the deck is deleted successfully, a 204 No Content response will be returned.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        path_params (Path[GetDeckIn]): The path parameters containing the deck ID to delete.

    Returns:
        None: If the deck is deleted successfully, a 204 No Content response will be returned. If the deck is not found or the user does not have permission to delete it, an appropriate HTTP error response will be returned.
    """
    user = get_user_from_request(request)
    deck = path_params.deck
    if deck.user.id != user.id:
        raise HttpError(403, "You do not have permission to access this deck")
    deck.delete()
    return None


@router.patch(
    '/{deck_id}/',
    summary='Update deck details',
    description='Update the details of a deck by its ID.',
    response={200: GetFullDeckOut},
    operation_id='update_deck',
)
def update_deck(request: HttpRequest, path_params: Path[GetDeckIn], payload: UpdateDeckIn) -> GetFullDeckOut:
    """
    Update the details of a deck by its ID.

    This endpoint allows you to update the details of a specific deck using its unique identifier.
    The response will include the updated information about the deck, such as its name, summary description, and full description.
    It does not allow updating the cards in the deck, only the metadata fields.

    Args:
        request (HttpRequest): The incoming HTTP request object.
        path_params (Path[GetDeckIn]): The path parameters containing the deck ID to update.
        payload (UpdateDeckIn): The request body containing the fields to update, such as the new name, short summary, and full summary of the deck.

    Returns:
        GetFullDeckOut: An object containing the full details of the updated deck, including its cards.
    """
    deck = path_params.deck
    user = get_user_from_request(request)
    if deck.user.id != user.id:
        raise HttpError(403, "You do not have permission to access this deck")
    if payload.name is not None:
        deck.name = payload.name
    if payload.short_summary is not None:
        deck.short_llm_summary = payload.short_summary
    if payload.full_summary is not None:
        deck.llm_summary = payload.full_summary
    deck.save()
    latest_build = _get_latest_build(str(deck.id))
    creation_status = latest_build.status if latest_build else None

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
        creation_status=creation_status,
    )


@router.get(
    '/daily_theme/',
    summary='Get daily deck theme',
    description='Retrieve the daily deck theme.',
    response={200: str},
    operation_id='get_daily_theme',
)
def get_daily_theme(request: HttpRequest) -> str:
    """
    Retrieve the daily deck theme.

    This endpoint allows you to fetch the daily deck theme, which is generated by an LLM and updated once per day.
    The response will include the theme as a string.

    Args:
        request (HttpRequest): The incoming HTTP request object.

    Returns:
        str: The daily deck theme as a string.
    """
    daily_theme = DailyDeckTheme.objects.order_by('-date').first()
    if daily_theme is None:
        return "Blue-White Control: counterspells, card draw, and versatile answers to threats, with a focus on controlling the game and winning in the late game."
    return daily_theme.theme
