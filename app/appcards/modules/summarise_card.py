from typing import Any, cast

from app.utils import in_celery_task
from appai.constants.llm_models import TEXT_MODEL
from appai.constants.prompt_gotchas import GOTCHAS
from beartype import beartype
from celery.result import AsyncResult
from pydantic_ai import Agent

from appcards.modules.card_info import CardInfo

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
"""


@beartype
def _summarise_card(card_details: CardInfo) -> str:
    agent = Agent(model=TEXT_MODEL, system_prompt=SUMMARY_PROMPT, instrument=True)
    data = card_details.model_dump_json(exclude={"id"})
    return agent.run_sync(data).output


@beartype
def summarise_card(card_details: CardInfo) -> str:
    if in_celery_task():
        from appcards.tasks.summarise_card import summarise_card as _summarise_card_task

        result: AsyncResult = cast(Any, _summarise_card_task.delay)(card_details.model_dump())
        return cast(str, result.get(timeout=90))
    else:
        return _summarise_card(card_details)
