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

from django.http import HttpRequest
from ninja import Path, Router

from appcards.constants.cards import HIERARCHICAL_TAGS, PRIMARY_TAG_DESCRIPTIONS
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

    tags: dict[str, dict[str, str]] = {}
    for primary_tag, subtags in HIERARCHICAL_TAGS.items():
        bucket: dict[str, str] = {}
        if primary_tag in used_tags:
            bucket[primary_tag] = PRIMARY_TAG_DESCRIPTIONS.get(primary_tag, "No description available")
        for subtag, description in subtags.items():
            if subtag in used_tags:
                bucket[subtag] = description
        tags[primary_tag] = bucket
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
