from django.http import HttpRequest
from ninja import Path, Router

from appcards.models.card import Card
from appcards.modules.card_info import CardInfo, card_to_info
from appcards.serializers.card import GetCardIn, SetCodesOut

router = Router(tags=['cards'])


@router.get(
    '/set_codes/',
    summary='List available set codes',
    description='Retrieve a list of all available set codes.',
    response={200: SetCodesOut},
    operation_id='list_set_codes',
)
def list_set_codes(request: HttpRequest) -> SetCodesOut:
    """
    try:
    -zNTA8iJe-WuzI0XrRESC

    Retrieve a list of all available set codes.

    This endpoint allows you to fetch the set codes that are currently available for deck construction.
    """
    set_codes = list(Card.objects.values_list('set_code', flat=True).distinct())
    return SetCodesOut(set_codes=set_codes)


@router.get(
    '/{card_id}/',
    summary='Get card details',
    description='Retrieve the details of a card by its ID.',
    response={200: SetCodesOut},
    operation_id='get_card',
)
def get_card(request: HttpRequest, path_params: Path[GetCardIn]) -> CardInfo:
    """
    PVn4yqXeYxd4O1rHEiOPp

    Retrieve the details of a card by its ID.

    This endpoint allows you to fetch the details of a specific card using its unique identifier.
    The response will include information about the card, such as its name, set code, and other relevant details.
    """
    card = path_params.card
    return card_to_info(card)
