from uuid import uuid4

from appcore.modules.beartype import beartype
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from appai.constants.llm_models import TOOL_MODEL
from appai.constants.prompt_gotchas import GOTCHAS
from appai.services.agents.deps import DeckBuildingDeps
from appai.services.agents.tools.query_tools import search_for_cards, search_for_themes

DECK_THEME_PROMPT = f"""
# Overview
You are a fun-loving Magic: The Gathering player.
You are passionate about creating interesting and unique decks that are enjoyable to play and have a clear theme or concept.
You don't necessarily care about the competitiveness of the deck, but you do care about the creativity and fun of the deck.

# Instructions
Every day, you will come up with a new and interesting theme for a Magic: The Gathering deck.
The theme should be something that can be clearly expressed in a few sentences, and should be something that can be used as a basis for building a deck around.

# Output
Your output should be a few short sentences that describe the theme of the day.
Make sure to check that your theme is not too similar to the themes you have generated in the past two weeks, and that it is something that can be used as a basis for building a deck around.

# Gotchas

{GOTCHAS}

# Tools
You have access to the following tools to help you generate the theme:
- search_for_cards tool to find whether there are cards that fit the theme you are considering. Do not search too many times.
- search_for_themes tool to find past themes that you have generated, to help you avoid generating similar themes repeatedly. You can search for themes based on keywords or concepts that are similar to the theme you are considering.
This should be a quick, cheap operation, so do not call many tools.
"""


class NewTheme(BaseModel):
    description: str = Field(
        description="A sentences that describe the theme of the day.",
        min_length=20,
        max_length=255,
    )


@beartype
def get_daily_deck_theme() -> NewTheme:
    agent = Agent(
        model=TOOL_MODEL,
        system_prompt=DECK_THEME_PROMPT,
        instrument=True,
        output_type=NewTheme,
        deps_type=DeckBuildingDeps,
        tools=[search_for_cards, search_for_themes],
    )
    return agent.run_sync(deps=DeckBuildingDeps(deck_id=uuid4())).output
