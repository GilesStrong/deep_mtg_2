from django.http import HttpRequest
from ninja import Path, Router

from appcards.constants.cards import HIERACHICAL_TAGS
from appcards.models.card import Card
from appcards.models.printing import Printing
from appcards.modules.card_info import CardInfo, card_to_info
from appcards.serializers.card import GetCardIn, SetCodesOut, SetTagsOut

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
    Retrieve a list of all available set codes.

    This endpoint allows you to fetch the set codes that are currently available for deck construction.
    """
    set_codes = list(Printing.objects.order_by('set_code').values_list('set_code', flat=True).distinct())
    return SetCodesOut(set_codes=set_codes)


@router.get(
    '/tags/',
    summary='List available tags',
    description='Retrieve a list of all available tags.',
    response={200: SetTagsOut},
    operation_id='list_tags',
)
def list_tags(request: HttpRequest) -> SetTagsOut:
    """
    Retrieve a list of all available tags.

    This endpoint allows you to fetch the tags that are currently available for deck construction.
    """
    tag_lists = Card.objects.values_list('tags', flat=True)
    used_tags = sorted({tag for tag_list in tag_lists for tag in (tag_list or [])})
    tags = {
        primary_tag: {subtag: description for subtag, description in subtags.items() if subtag in used_tags}
        for primary_tag, subtags in HIERACHICAL_TAGS.items()
    }
    return SetTagsOut(tags=tags)


@router.get(
    '/{card_id}/',
    summary='Get card details',
    description='Retrieve the details of a card by its ID.',
    response={200: CardInfo},
    operation_id='get_card',
)
def get_card(request: HttpRequest, path_params: Path[GetCardIn]) -> CardInfo:
    """
    Retrieve the details of a card by its ID.

    This endpoint allows you to fetch the details of a specific card using its unique identifier.
    The response will include information about the card, such as its name, set code, and other relevant details.
    """
    card = path_params.card
    return card_to_info(card)
