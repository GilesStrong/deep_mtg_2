from aiocache import cached
from appcards.constants.cards import EVERGREEN_KEYWORDS
from appcards.models.card import ManaColorEnum, Rarity, TypeEnum
from appcards.modules.card_info import CardInfo
from appsearch.services.qdrant.search_dsl import (
    Condition,
    Filter,
    MatchAnyCondition,
    MatchValueCondition,
)
from beartype import beartype
from pydantic_ai import Agent, ModelRetry

from appai.constants.llm_models import TOOL_MODEL

METADATA_FILTER_FIELDS = [
    'subtypes',
    'supertypes',
    'power',
    'toughness',
    'mana_cost_red',
    'mana_cost_blue',
    'mana_cost_green',
    'mana_cost_white',
    'mana_cost_black',
    'mana_cost_colorless',
    'converted_mana_cost',
    'colors',
    'types',
    'rarity',
    'keywords',
]


def _get_metadata_fields() -> str:
    field_descriptions = ""
    for name, desc in CardInfo.model_fields.items():
        if name not in METADATA_FILTER_FIELDS:
            continue
        field_descriptions += f"{name}: {desc.annotation} {desc.description}\n"
    return field_descriptions


METADATA_FIELD_DESCRIPTIONS = _get_metadata_fields()


@beartype
def validate_card_filter(card_filter: Filter) -> None:
    """
    Validates a card filter to ensure all conditions use valid fields and values.

    This function checks that:
    - All condition keys are valid metadata filter fields
    - Keywords are evergreen keywords when filtering by 'keywords'
    - Colors are valid mana colors when filtering by 'colors'
    - Rarities are valid rarity values when filtering by 'rarity'
    - Types are valid type enum values when filtering by 'types'
    - Numeric fields (power, toughness, mana costs) contain integer values

    Args:
        card_filter (Filter): The filter object containing should, must, and must_not conditions
            to validate.

    Raises:
        ModelRetry: If any condition contains an invalid field name, keyword, color, rarity,
            type, or non-integer value for numeric fields.

    Returns:
        None: This function validates in place and raises exceptions on invalid input.
    """

    def _validate_condition(condition: Condition) -> None:
        if condition.key not in METADATA_FILTER_FIELDS:
            raise ModelRetry(f"Invalid filter field: {condition.key}")
        if condition.key == 'keywords':
            if isinstance(condition, MatchAnyCondition):
                for keyword in condition.any:
                    if keyword not in EVERGREEN_KEYWORDS:
                        raise ModelRetry(f"Invalid keyword filter: {keyword} is not an evergreen keyword")
            elif isinstance(condition, MatchValueCondition):
                if condition.value not in EVERGREEN_KEYWORDS:
                    raise ModelRetry(f"Invalid keyword filter: {condition.value} is not an evergreen keyword")
        if condition.key == 'colors':
            if isinstance(condition, MatchAnyCondition):
                for color in condition.any:
                    if color not in ManaColorEnum._value2member_map_:
                        raise ModelRetry(f"Invalid color filter: {color} is not a valid mana color")
            elif isinstance(condition, MatchValueCondition):
                if condition.value not in ManaColorEnum._value2member_map_:
                    raise ModelRetry(f"Invalid color filter: {condition.value} is not a valid mana color")
        if condition.key == 'rarity':
            if isinstance(condition, MatchAnyCondition):
                for rarity in condition.any:
                    if rarity not in Rarity._value2member_map_:
                        raise ModelRetry(f"Invalid rarity filter: {rarity} is not a valid rarity")
            elif isinstance(condition, MatchValueCondition):
                if condition.value not in Rarity._value2member_map_:
                    raise ModelRetry(f"Invalid rarity filter: {condition.value} is not a valid rarity")
        if condition.key == 'types':
            if isinstance(condition, MatchAnyCondition):
                for kind in condition.any:
                    if kind not in TypeEnum._value2member_map_:
                        raise ModelRetry(f"Invalid type filter: {kind} is not a valid type")
            elif isinstance(condition, MatchValueCondition):
                if condition.value not in TypeEnum._value2member_map_:
                    raise ModelRetry(f"Invalid type filter: {condition.value} is not a valid type")
        if condition.key in [
            'converted_mana_cost',
            'mana_cost_red',
            'mana_cost_blue',
            'mana_cost_green',
            'mana_cost_white',
            'mana_cost_black',
            'mana_cost_colorless',
        ]:
            if isinstance(condition, MatchValueCondition):
                if type(condition.value) is not int:
                    raise ModelRetry(f"Invalid numeric filter: {condition.value} is not a valid integer")
            elif isinstance(condition, MatchAnyCondition):
                for value in condition.any:
                    if type(value) is not int:
                        raise ModelRetry(f"Invalid numeric filter: {value} is not a valid integer")
            # Don't need to validate range conditions here, since Pydantic will ensure the values are the correct type

        if condition.key in ['power', 'toughness']:
            if isinstance(condition, MatchValueCondition):
                if type(condition.value) is not str:
                    raise ModelRetry(f"Invalid string filter: {condition.value} is not a valid string")
            elif isinstance(condition, MatchAnyCondition):
                for value in condition.any:
                    if type(value) is not str:
                        raise ModelRetry(f"Invalid string filter: {value} is not a valid string")

    for condition in card_filter.should + card_filter.must + card_filter.must_not:
        _validate_condition(condition)


FILTER_CONSTRUCTION_PROMPT = f"""
# Overview
You are an expert Magic: The Gathering player helping to search through a database of cards.
The database contains detailed information about each card, including its name, type, mana cost, abilities, and more.
Cards are stored based on metadata, which you can filter on
You are given a search query and your task is to construct filters for cards based on the query in order to help the user find the cards they are looking for.

# Instructions
Given the user's search query, identify the relevant metadata fields and values that can be used to filter the cards in the database.
Construct a Filter object that represents the filters for searching cards based on the query.
You do not need to be overly specific with the filters, just identify the relevant fields and values that can be used to filter out cards that will definitely be undesirable.
If you are unable to fully specify a good filter based on the query, that's okay. Just specify the filters that you can be reasonably sure about based on the query.

## Example
Query: "I want cheap red creatures with flying"
Should filter on colors to be red only, creature type, low converted mana cost, and keywords containing flying.

# Metadata Fields
{METADATA_FIELD_DESCRIPTIONS}

## Notes
If filtering on keywords, only filter on evergreen keywords, which are the most commonly used keywords in Magic: The Gathering.
The following are the current set of evergreen keywords: {EVERGREEN_KEYWORDS}

# Input
The input will be a search query string provided by the user in natural language.

# Output
The output should be a Filter object that contains the filters for searching cards based on the user's query
The output model is a part of a qdrant DSL represented by a pydantic model.
The final filter will be created based on your response.
"""


@cached(ttl=3600)  # Cache for 1 hour
@beartype
async def filter_constructor(query: str) -> Filter:
    """
    Construct filters for cards based on a query string.

    Args:
        query (str): The search query.

    Returns:
        Filter: A Filter object containing the filters for searching cards.
    """

    agent = Agent(
        model=TOOL_MODEL,
        system_prompt=FILTER_CONSTRUCTION_PROMPT,
        output_retries=10,
        output_type=Filter,
        instrument=True,
    )

    @agent.output_validator
    async def _validate_output(output: Filter) -> Filter:
        validate_card_filter(output)
        return output

    response = await agent.run(query)
    return response.output
