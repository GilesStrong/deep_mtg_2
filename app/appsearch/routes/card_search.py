from appauth.modules.auth_rate_limit import check_auth_rate_limit
from appcards.constants.storage import CARD_COLLECTION_NAME
from appcards.models.card import Card
from appcards.modules.card_info import card_to_info
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from appsearch.serializers.card_search import FoundCard, SearchCardsIn, SearchCardsOut
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Filter, MatchAnyCondition, Query

router = Router(tags=['cards'])

SEARCH_LIMIT_PER_FIVE_SECONDS = 1
SEARCH_LIMIT_PER_MINUTE = 10
SEARCH_LIMIT_PER_HOUR = 100
CARD_SEARCH_TOP_K = 25


def _check_search_rate_limit(request: HttpRequest) -> None:
    """
    Enforce the card search rate limit for the requesting client.

    Args:
        request: The incoming request used to derive the rate-limit key.

    Raises:
        HttpError: If card search requests exceed the configured limits.
    """

    # Ensure all rate limits are checked and the most restrictive one is enforced
    short_rate_limit = check_auth_rate_limit(
        request,
        action='card-search',
        limit=SEARCH_LIMIT_PER_FIVE_SECONDS,
        window_seconds=5,
    )
    medium_rate_limit = check_auth_rate_limit(
        request,
        action='card-search',
        limit=SEARCH_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
    long_rate_limit = check_auth_rate_limit(
        request,
        action='card-search',
        limit=SEARCH_LIMIT_PER_HOUR,
        window_seconds=3600,
    )

    if not short_rate_limit.allowed:
        raise HttpError(429, f'Too many card search attempts. Retry in {short_rate_limit.retry_after_seconds}s')

    if not medium_rate_limit.allowed:
        raise HttpError(429, f'Too many card search attempts. Retry in {medium_rate_limit.retry_after_seconds}s')

    if not long_rate_limit.allowed:
        raise HttpError(429, f'Too many card search attempts. Retry in {long_rate_limit.retry_after_seconds}s')


@router.post(
    '/search/',
    summary='Search for cards',
    description='Search for cards based on a query string.',
    response={200: SearchCardsOut},
    operation_id='search_cards',
)
def search_cards(request: HttpRequest, payload: SearchCardsIn) -> SearchCardsOut:
    """
    Search for cards based on a query string and filters.
    Searches are limited to a certain number per hour to prevent abuse.

    Args:
        request (HttpRequest): The incoming HTTP request object, used to identify the user making the request.
        payload (SearchCardsIn): An object containing the search query string and filters such as tags, set codes, and colors.

    Returns:
        SearchCardsOut: An object containing a list of card information objects and their relevance scores that match the search criteria.
    """
    _check_search_rate_limit(request)
    query = payload.query
    set_codes = payload.set_codes
    colors = [color.value for color in payload.colors]
    tags = payload.tags

    # Build filter
    must = []
    if len(set_codes) > 0:
        must.append(MatchAnyCondition(key="set_codes", any=set_codes))
    if len(colors) > 0:
        must.append(MatchAnyCondition(key="colors", any=colors))
    if len(tags) > 0:
        must.append(MatchAnyCondition(key="tags", any=tags))
    card_filter = Filter(
        must=must,  # type: ignore[arg-type]
    )

    # Run search
    found_cards = run_query_from_dsl(
        Query(collection_name=CARD_COLLECTION_NAME, query_string=query, filter=card_filter, limit=CARD_SEARCH_TOP_K),
    )

    # Convert results to CardInfo
    card_infos = []
    for point in found_cards:
        try:
            card = Card.objects.get(id=point.id)
            card_infos.append(FoundCard(card_info=card_to_info(card), relevance_score=point.score))
        except Card.DoesNotExist:
            continue
    return SearchCardsOut(cards=card_infos)
