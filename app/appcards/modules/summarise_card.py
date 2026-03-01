import json
from typing import Any, cast

from app.utils import in_celery_task
from appai.constants.llm_models import TEXT_MODEL
from appai.constants.prompt_gotchas import GOTCHAS
from appcore.modules.beartype import beartype
from celery.result import AsyncResult
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from appcards.constants.cards import CARD_TAGS
from appcards.modules.card_info import CardInfo


class CardSummary(BaseModel):
    summary: str = Field(
        ...,
        description="A concise summary of the card, written in natural language, that captures the key details and overall impression of the card, without going into excessive detail.",
    )
    tags: list[str] = Field(
        ...,
        description="A list of tags that categorise the card based on its attributes and potential roles in a deck. Tags should be selected from a predefined set of categories that reflect the card's mechanics, strengths, weaknesses, and synergies with other cards or strategies.",
    )

    @field_validator("tags", mode="before")
    def validate_tags(cls, value: list[str]) -> list[str]:
        invalid_tags = [tag for tag in value if tag not in CARD_TAGS]
        if invalid_tags:
            raise ValueError(f"Invalid tags: {', '.join(invalid_tags)}. Valid tags are: {', '.join(CARD_TAGS.keys())}")
        return value


SUMMARY_PROMPT = f"""
# Overview
You are an expert Magic: The Gathering player.
You are helping a new player to understand what various cards do from a high-level perspective.

# Instructions
When provided with a card, you should write a concise summary of the card from the point of view of the owner of the card.
You can assume that the player understands the basic rules of the game
Include basic keyword terms like 'flying' or 'trample', but do not explain what they mean.
Do not include details of rarity or set information.
Rather than quantifying attributes of the card, instead use qualitative terms like 'strong' or 'weak' to describe the card.
Include the name of the card in the summary.
Include details of the card's role in that, strengths, and weaknesses.
Include the mana colors of the card, along with the a qualitative description of the mana cost.
Do not return anything other than the summary of the card.
Make sure to check that your summary accurately reflects the card.

{GOTCHAS}

# Input
The input will be a collection of details about the card in the form of a JSON dump.

# Output
A concise summary of the card, written in natural language, that captures the key details and overall impression of the card, without going into excessive detail.
Do not include additional statements or explanations outside of the summary.

The summary should cover:
- The colours of the card
- The role of the card in a deck
- The strengths of the card
- The weaknesses of the card
- Potential synergies with other cards or strategies (do not name specific cards)

Additionally, you should also include a list of tags that categorise the card based on its attributes and potential roles in a deck.
The list of available tags are as follows, along with their meanings:
{json.dumps(list(CARD_TAGS.keys()), indent=2, ensure_ascii=False)}
A card can have multiple tags, but try to limit the number of tags to the most relevant ones that capture the essence of the card.
Tags may have overlap with each other, e.g. a card that is tagged as 'Aggro' may also be tagged as 'Weenie', so use these more general tags in addition to more specific tags, too.
"""


@beartype
def _summarise_card(card_details: CardInfo) -> CardSummary:
    agent = Agent(model=TEXT_MODEL, system_prompt=SUMMARY_PROMPT, instrument=True, output_type=CardSummary)
    data = card_details.model_dump_json(exclude={"id"})
    return agent.run_sync(data).output


@beartype
def summarise_card(card_details: CardInfo) -> CardSummary:
    if in_celery_task():
        from appcards.tasks.summarise_card import summarise_card as _summarise_card_task

        result: AsyncResult = cast(Any, _summarise_card_task.delay)(card_details.model_dump())
        summary = cast(dict[str, str | list[str]], result.get(timeout=90))
        return CardSummary.model_validate(summary)
    else:
        return _summarise_card(card_details)
