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

from appcards.constants.cards import EVERGREEN_KEYWORDS
from appcore.modules.beartype import beartype
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from appai.constants.llm_models import TOOL_MODEL_BASIC
from appai.constants.prompt_gotchas import GOTCHAS
from appai.services.agents.deps import MAX_THEME_SEARCHES, ThemeDeps
from appai.services.agents.tools.query_tools import find_similar_themes

MIN_LENGTH = 20
MAX_LENGTH = 255

DECK_THEME_PROMPT = f"""
# Overview
You are a fun-loving Magic: The Gathering player.
You are passionate about creating interesting and unique decks that are enjoyable to play and have a clear theme or concept.
You don't necessarily care about the competitiveness of the deck, but you do care about the creativity and fun of the deck.

# Instructions
Every day, you will come up with a new and interesting theme for a Magic: The Gathering deck.
The theme should be something that can be clearly expressed in a few sentences, and should be something that can be used as a basis for building a deck around.
The theme should be broad enough that the deck can be built in a variety of ways, without relying on a specific mechanic or card, which may not be legal or available in the format of the deck.
However the theme should be specific enough that it provides a clear direction for building a deck, and is not something generic like "a fun deck" or "a deck with lots of creatures".
Do not over think things, just come up with a fun and interesting theme that you think would be enjoyable to build a deck around.
When using the find_similar_themes tool, if no similar themes exist, that's great! That means you have come up with a unique and interesting theme that hasn't been done before, so just go with it!

If you wish to include specific keywords, only use evergreen keywords that are not likely to rotate out of standard, and avoid using very specific mechanics that may only be present in a few cards.
The current set of evergreen keywords are: {EVERGREEN_KEYWORDS}.
However, in general, err on the side of including general descriptions for what the mechanics should accomplish, rather than how they may be specified on the cards.

You general flow should be:
1. Come up with a theme based on your creativity and knowledge of Magic: The Gathering.
2. Check if the theme is similar to any themes you have generated in the past using the find_similar_themes tool, to ensure you are not generating similar themes repeatedly.
3. If the theme is similar to past themes, modify it to make it more unique and interesting, and check again for similarity until you have a theme that is not similar to past themes.
4. If it is not similar to past themes, then you can go with it and finish.

# Output
Your output should be a few short sentences that describe the theme of the day.
Make sure to check that your theme is not too similar to the themes you have generated in the past, and that it is something that can be used as a basis for building a deck around.
The theme description must be between {MIN_LENGTH} and {MAX_LENGTH} characters in length.

# Gotchas
{GOTCHAS}

# Tools
You have access to the following tools to help you generate the theme:
- find_similar_themes tool to check that your theme is not too similar what you have generated in the past, to help you avoid generating similar themes repeatedly.
  - Do not make generic searches, like "fun themes". Instead, send the exact theme you are considering as the search query.
  - Do not use the tool to get inspiration for your theme, instead only use it to ensure your idea is unique. 
This should be a quick, cheap operation, so do not call many tools.
You can make a maximum of {MAX_THEME_SEARCHES} calls to the find_similar_themes tool during this process, so use it wisely to check for similarity against your current theme idea.
"""


class NewTheme(BaseModel):
    description: str = Field(
        description="A few sentences that describe the theme of the deck. Do not include any prefix like 'the theme of the deck is...', just the description of the theme itself. The description should be specific enough to provide a clear direction for building a deck, but not so specific that it relies on a particular card or mechanic.",
        min_length=MIN_LENGTH,
        max_length=MAX_LENGTH,
    )


@beartype
def get_daily_deck_theme() -> NewTheme:
    """
    Generate a new daily deck theme for Magic: The Gathering using an AI agent.

    This function initializes an AI agent with deck-building capabilities and runs it
    synchronously to produce a new theme suggestion for a Magic: The Gathering deck.

    The agent is equipped with tools to search for previously generated themes.

    Returns:
        NewTheme: A new deck theme object containing the AI-generated theme
                  suggestion for the day, including relevant cards and theme details.
    """
    agent = Agent(
        model=TOOL_MODEL_BASIC,
        system_prompt=DECK_THEME_PROMPT,
        name="Daily Deck Theme Agent",
        model_settings={'thinking': False},
        instrument=True,
        output_type=NewTheme,
        tools=[find_similar_themes],
        retries=1,
        output_retries=3,
        deps_type=ThemeDeps,
    )
    deps = ThemeDeps(n_searches=0)
    return agent.run_sync(deps=deps).output
