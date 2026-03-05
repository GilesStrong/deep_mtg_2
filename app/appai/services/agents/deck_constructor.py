import json
from typing import Optional
from uuid import UUID

from app.app_settings import APP_SETTINGS
from appcards.constants.cards import CARD_IMPORTANCES, CARD_ROLES, CURRENT_STANDARD_SET_CODES
from appcards.constants.decks import DECK_CLASSIFICATIONS, GROUPED_DECK_CLASSIFICATIONS
from appcards.models.card import Card
from appcards.models.deck import (
    MAX_DECK_NAME_LENGTH,
    SHORT_SUMMARY_LENGTH_LIMIT,
    SUMMARY_LENGTH_LIMIT,
    Deck,
    DeckCard,
)
from appcore.modules.beartype import beartype
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field, create_model, field_validator
from pydantic_ai import Agent, ModelRetry, UsageLimits

from appai.constants.llm_models import TOOL_MODEL_BASIC, TOOL_MODEL_THINKING
from appai.constants.prompt_gotchas import GOTCHAS
from appai.services.agents.deps import DeckBuildingDeps
from appai.services.agents.tools.card_tools import inspect_card
from appai.services.agents.tools.deck_tools import (
    add_card_to_deck,
    clear_deck,
    list_deck_cards,
    remove_card_from_deck,
    validate_deck,
)
from appai.services.agents.tools.query_tools import search_for_cards

DECK_CONSTRUCTION_SYSTEM_PROMPT = f"""
# Overview
You are an expert Magic: The Gathering deck builder. 
Your task is to construct a standard-legal 60-card deck based on the description provided by the user.
Use the tools available to you to build the deck step by step, ensuring that you follow the user's instructions and any constraints they have provided.

# Input
The user will provide a natural language description of the deck they want to build, or how they want the existing deck to be modified (Generation request).
You should interpret this description to understand the strategy, key cards, and any specific requirements or constraints for the deck.
Aim to stick as closely as possible to the user's description, while also ensuring that the deck is legal and follows any constraints provided.

If this is not the first time the user has requested a generation for this deck, you will also be provided with:
- The current name of the deck, feel free to modify the name as you see fit to better reflect the strategy and key features of the deck as it evolves through the generation process.
- The current summary of the deck, which includes its strategy, key cards, and how it meets the user's requirements based on the last generation. Use this summary to understand the current state of the deck and to inform your next steps in the construction process.
- A history of previous generations for this deck (Previous generation history).
Use this history to inform your construction process, ensuring that you build upon previous generations and make improvements based on the feedback and results of those generations.
Use the history to also avoid changing the deck in ways that have already been tried and did not work, unless the user specifically requests to go in a different direction.
Additionally, use the history to understand the original purpose and strategy of the deck when the current generation request is to modify an existing deck rather than build a new deck from scratch and does not include a detailed description of the desired deck.

# Output
You will not output the final deck directly. Instead, you will use the available tools to build the deck iteratively.

You output will instead consist of summary aspects of the deck:
## Summary
A long-form final summary of the deck, including its strategy, key cards.
Do not refer to the user's original description in the summary, or mention changes that were made to an existing deck.
Instead, this should be a standalone description of the deck that could be read and understood without reference to the user's original description or the previous state of the deck.

## Short summary
A short, snappy catchline for the deck. ~15 words. Suitable for use when viewing multiple decks side by side to help distinguish them.

## Name
A name for the deck that reflects its strategy and key features.

## Tags
A list of tags that describe the deck, which classify how the deck plays. Tags should be selected from a predefined set of categories that reflect the deck's strategy, playstyle, and key features:
{json.dumps(GROUPED_DECK_CLASSIFICATIONS, indent=2, ensure_ascii=False)}
This is a grouped classification: the tags are the inner keys, within the broader groups of deck classifications.
Normally, a deck would only have upto one tag from each group, but it is possible to have multiple tags from the same group if the deck has multiple distinct strategies or features that are relevant to that group.

# Deck state and tools
The state of the deck will be maintained through the tools you use:
- list_deck_cards tool to check the current state of the deck at any time.
- add_card_to_deck and remove_card_from_deck tools to modify the deck by adding or removing cards.
- search_for_cards tool to find cards that match specific criteria or fit the strategy of the deck. Do not search for specific cards by name, but rather describe the type of card you are looking for based on its characteristics, role in the deck, or how it fits into the overall strategy.
- validate_deck tool to check the legality of the deck.
- inspect_card tool to get detailed information about specific cards, which can help you understand how they fit into the deck and whether they meet the user's requirements.

# Considerations:
- When choosing cards to add to the deck, consider how they fit with the overall strategy and synergy of the deck, as well as any specific requirements or constraints provided by the user.
  - What role does the card play in the deck? Is it a win condition, a piece of interaction, a mana source, or something else?
  - How does the card synergize with other cards in the deck? Does it enable or enhance the effectiveness of other cards, or does it work well on its own?
  - What strengths of the deck does the card contribute to? Does it help the deck to achieve its main strategy, or does it provide support in other ways?
  - What weaknesses of the deck does the card help to mitigate? Does it provide answers to common threats, or does it help to shore up any weaknesses in the deck's strategy?
  - Is the card affordable in terms of mana cost and mana colors that the deck can produce? If not, is it worth adjusting the mana base to accommodate the card, or should it be avoided in favor of a more affordable option?
- Consider the balance of the deck, including the mana curve, the mix of card types, and the overall consistency of the deck.
- Do not assume names of specific cards, beyond basic lands. The legal sets are constantly changing, so you cannot rely on prior knowledge of specific cards being available.

## General flow:
Remember, a deck must have at least 60 cards, and no more than 4 copies of any individual card (other than basic lands).
Cards require mana to cast, so ensure that the deck has a sufficient mana base to support the cards included in the deck.
In general, a 60-card deck contains around 24 lands, but this can vary based on the strategy of the deck and the mana costs of the cards included.

In general, you should aim to build the deck iteratively, starting with a core strategy and key cards, and then filling in the rest of the deck with supporting cards and a suitable mana base.
1. Read the current deck list using the list_deck_cards tool; you may well be required to finish or modify an existing deck, so understanding the current state of the deck is essential before making changes.
2. Based on the core strategy, build a mana base based on the expected colors and mana costs of the cards that will be included in the deck. This can be refined later on.
3. Add the key cards that are central to the deck's strategy, ensuring that you include enough copies of each card to maximize the effectiveness of the deck.
4. Fill in the rest of the deck with supporting cards that enhance the overall strategy and synergy of the deck, while also considering the balance of the deck.
5. Finalise the mana base, ensuring that it can support the cards included in the deck and provides a good balance of colors and mana costs.
6. Review the deck to ensure that it meets the user's requirements and constraints, and that it is a cohesive and effective deck that follows the core strategy.
7. Use the rename_deck tool to give the deck a name that reflects its strategy and key features.
8. Validate the deck using the validate_deck tool to ensure that it is legal and meets all necessary requirements.

A successful deck ensures that all cards work together to achieve a common strategy, and that the deck is consistent and effective in executing that strategy.
It needs to ensure that it is able to survive the early game, establish its strategy in the mid game, and have a plan or win condition for in the late game.
Unless going for a fast agro deck, staying on curve and ensuring card draw and mana sources in the early-mid game is essential.

{GOTCHAS}
"""


class DeckConstructionOutput(BaseModel):
    deck_name: str = Field(
        ...,
        description=f"The name of the deck, reflecting its strategy and key features. {MAX_DECK_NAME_LENGTH} characters max.",
        min_length=1,
        max_length=MAX_DECK_NAME_LENGTH,
    )
    summary: str = Field(
        ...,
        description=f"A summary of the deck that was constructed, including its strategy, key cards, and how it meets the user's requirements. {SUMMARY_LENGTH_LIMIT[1]} characters max.",
        min_length=SUMMARY_LENGTH_LIMIT[0],
        max_length=SUMMARY_LENGTH_LIMIT[1],
    )
    short_summary: str = Field(
        ...,
        description=f"A short, snappy catchline for the deck. ~15 words, {SHORT_SUMMARY_LENGTH_LIMIT[1]} characters max. Suitable for use when viewing multiple decks side by side to help distinguish them.",
        min_length=SHORT_SUMMARY_LENGTH_LIMIT[0],
        max_length=SHORT_SUMMARY_LENGTH_LIMIT[1],
    )
    tags: list[str] = Field(
        default_factory=list,
        description="A list of tags that describe the deck, which classify how the deck plays.",
    )

    @field_validator("tags", mode="after")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        invalid_tags = [tag for tag in value if tag not in DECK_CLASSIFICATIONS]
        if invalid_tags:
            raise ValueError(
                f"Invalid tags: {', '.join(invalid_tags)}. Valid tags are: {', '.join(DECK_CLASSIFICATIONS.keys())}"
            )
        value = list(set(value))
        return value


@beartype
async def run_deck_constructor_agent(
    deck_id: UUID, deck_description: str, generation_history: list[str], available_set_codes: Optional[set[str]] = None
) -> DeckConstructionOutput:
    """
    Constructs a deck based on a natural language description.
    This function uses an agent to interpret the description and perform the necessary operations to build the deck.

    Args:
        deck_id (UUID): The ID of the deck to construct.
        deck_description (str): A natural language description of the desired deck, including its strategy, key cards, and any specific requirements or constraints.
        generation_history (list[str]): A list of previous generation requests for the deck, used to inform the construction process.
        available_set_codes (Optional[set[str]]): An optional set of available set codes to restrict the card selection to specific sets. If not provided, it will default to the current standard set codes.
    """

    agent = Agent(
        system_prompt=DECK_CONSTRUCTION_SYSTEM_PROMPT,
        model=TOOL_MODEL_THINKING,
        deps_type=DeckBuildingDeps,
        tools=[
            list_deck_cards,
            add_card_to_deck,
            remove_card_from_deck,
            search_for_cards,
            inspect_card,
            validate_deck,
            clear_deck,
        ],
        instrument=True,
        retries=10,
        output_retries=10,
        output_type=DeckConstructionOutput,
    )
    deps = DeckBuildingDeps(
        deck_id=deck_id,
        deck_description=deck_description,
        available_set_codes=available_set_codes if available_set_codes is not None else CURRENT_STANDARD_SET_CODES,
    )

    deck = await Deck.objects.aget(id=deck_id)
    input_message = f"# Generation request\n{deck_description}"
    # Append previous details
    if deck.name != "New Deck":
        input_message += f"\n\n# Current deck name\n{deck.name}"
    if deck.llm_summary is not None:
        input_message += f"\n\n# Current deck summary\n{deck.llm_summary}"
    if len(generation_history) > 0:
        input_message += "\n\n# Previous generation history"
        for i, previous_request in enumerate(generation_history):
            input_message += f"\n## Generation {i + 1}\n{previous_request}"
    if deck.tags is not None and len(deck.tags) > 0:
        input_message += f"\n\n# Current deck tags\n{', '.join(deck.tags)}"

    response = await agent.run(
        input_message,
        deps=deps,
        usage_limits=UsageLimits(
            request_limit=APP_SETTINGS.MAX_AGENT_CALLS_PER_TASK,
            input_tokens_limit=APP_SETTINGS.MAX_AGENT_INPUT_TOKENS,
            output_tokens_limit=APP_SETTINGS.MAX_AGENT_OUTPUT_TOKENS,
        ),
    )

    deck = await Deck.objects.aget(
        id=deck_id
    )  # Refetch the deck to get the latest state after modifications by the agent
    deck.name = response.output.deck_name
    deck.llm_summary = response.output.summary
    deck.short_llm_summary = response.output.short_summary
    deck.tags = response.output.tags
    if deck.generation_history is None:
        deck.generation_history = []
    deck.generation_history.append(deck_description)
    await deck.asave()
    return response.output


CARD_CLASSIFIER_SYSTEM_PROMPT = f"""
# Overiew
You are an expert Magic: The Gathering deck builder.
You have just finished constructing a deck, and are now in the process of explaining the roles of the card choices in the deck.
For each card in the deck, classify the card based on its role in the deck, and how replacebable it is with other cards that serve a similar role.

# Input
You will be provided with:
- The deck description, explaining the strategy of the deck
- The list of the cards in the deck, along with their quantities and details.

# Output
For each card in the deck, classify the card based on its role in the deck, and how replaceable it is with other cards that serve a similar role.
The classification should be based on the following categories:
{json.dumps(CARD_ROLES, indent=2, ensure_ascii=False)}
The importance of each card should be based on the following categories:
{json.dumps(CARD_IMPORTANCES, indent=2, ensure_ascii=False)}

# Considerations
Identify the win conditions and key synergies within the deck based on the deck description and the cards included in the deck.
Consider how unique the cards are in their role within the deck, and how easily they could be replaced by other cards that serve a similar function.

{GOTCHAS}
"""


@beartype
async def run_card_classifier_agent(deck_id: UUID, deck_description: str) -> None:
    """
    Classifies cards in a deck by their role and importance using an AI agent.

    This function fetches all cards associated with a given deck, formats them
    into a structured message, and runs an AI classification agent to determine
    each card's role and importance within the context of the deck's strategy.
    The results are then persisted back to the database.

    Args:
        deck_id (UUID): The unique identifier of the deck whose cards will be classified.
        deck_description (str): A natural language description of the deck's strategy
            and goals, used to provide context for the classification.

    Returns:
        None

    Raises:
        UsageLimitExceeded: If the agent exceeds the configured limits for requests,
            input tokens, or output tokens during classification.
        ValidationError: If the agent's output does not conform to the dynamically
            generated Pydantic model after the maximum number of output retries.
    """
    deck_cards: list[DeckCard] = await sync_to_async(list)(  # type: ignore [call-arg]
        DeckCard.objects.filter(deck_id=deck_id).select_related('card', 'deck')
    )

    card_ids: list[str] = []
    card_list: list[str] = []
    model_args: dict[str, type] = {}
    for i, deck_card in enumerate(deck_cards):
        card_id = f"{i:02d}"  # Save a few tokens using idex over UUID
        card_ids.append(card_id)
        card_list.append(
            f"""
# {deck_card.quantity}x {deck_card.card.name} -- card ID: {card_id}:
## Tags:{deck_card.card.tags}
## LLM Summary:
# {deck_card.card.llm_summary}
"""
        )
        model_args[f"card_id_{card_id}_role"] = str
        model_args[f"card_id_{card_id}_importance"] = str

    output_type = create_model(  # type: ignore [call-overload]
        "CardClassificationOutput",
        __base__=BaseModel,
        __config__=None,
        **model_args,  # type: ignore [call-arg]
    )

    message = f"# Deck description\n{deck_description}\n\n# Cards in deck\n{''.join(card_list)}"

    agent = Agent(
        system_prompt=CARD_CLASSIFIER_SYSTEM_PROMPT,
        model=TOOL_MODEL_BASIC,
        tools=[],
        instrument=True,
        retries=0,
        output_retries=10,
        output_type=output_type,
    )

    response = await agent.run(
        message,
        usage_limits=UsageLimits(
            request_limit=APP_SETTINGS.MAX_AGENT_CALLS_PER_TASK,
            input_tokens_limit=APP_SETTINGS.MAX_AGENT_INPUT_TOKENS,
            output_tokens_limit=APP_SETTINGS.MAX_AGENT_OUTPUT_TOKENS,
        ),
    )

    classifications = response.output.model_dump()
    for card_id in card_ids:
        role = classifications.get(f"card_id_{card_id}_role")
        importance = classifications.get(f"card_id_{card_id}_importance")
        if role is not None and importance is not None:
            index = int(card_id)
            deck_card = deck_cards[index]
            deck_card.role = role
            deck_card.importance = importance
            await deck_card.asave(update_fields=["role", "importance"])


CARD_REPLACEMENT_SYSTEM_PROMPT = """
# Overview
You are an expert Magic: The Gathering deck builder.
Given an existing deck, and a specific card in that deck, your role is to search for potential replacement cards that could be swapped in place of the specified card, and classify how good of a replacement each card is based on how well it fits the role of the original card in the deck, and how well it synergises with the rest of the deck.

# Input
You will be provided with:
- The deck description, explaining the strategy of the deck.
- The specific card to be replaced, along with its role and importance in the deck.
- A set of potential replacement cards, along with their details.

# Output
Given the set of potential replacement cards, return the list of card IDs that would be good replacements.
If there are no suitable replacements, return an empty list.
"""


@beartype
async def run_card_replacement_agent(
    deck_strategy: str, card_to_replace: DeckCard, potential_replacements: list[Card]
) -> list[UUID]:
    """
    Runs an AI agent to select replacement cards for a given card in a Magic: The Gathering deck.

    This agent analyzes the deck strategy and the card to be replaced, then selects
    appropriate replacements from a list of potential candidates. The agent validates
    that all returned card IDs are present in the provided list of potential replacements,
    retrying if invalid IDs are returned.

    Args:
        deck_strategy (str): A description of the deck's overall strategy and goals,
            used to guide the replacement selection.
        card_to_replace (DeckCard): The card that needs to be replaced, including its
            role, importance, tags, and LLM-generated summary within the deck context.
        potential_replacements (list[Card]): A list of candidate cards that could
            replace the original card, each containing tags and an LLM-generated summary.

    Returns:
        list[UUID]: A list of UUIDs representing the selected replacement cards from
            the potential_replacements list, ordered by suitability.
    """
    valid_uuids = [card.id for card in potential_replacements]

    agent = Agent(
        system_prompt=CARD_REPLACEMENT_SYSTEM_PROMPT,
        model=TOOL_MODEL_BASIC,
        tools=[],
        instrument=True,
        retries=0,
        output_retries=10,
        output_type=list[UUID],
    )

    @agent.output_validator
    async def _validate_output(output: list[UUID]) -> list[UUID]:
        for card_id in output:
            if card_id not in valid_uuids:
                raise ModelRetry(
                    f"Invalid card ID in output: {card_id}. Valid card IDs are: {', '.join(str(uuid) for uuid in valid_uuids)}"
                )
        return output

    card_list = "\n".join(
        f"""## {card.name} -- card ID: {card.id}:
### Tags:{card.tags}
### LLM Summary:
{card.llm_summary}
"""
        for card in potential_replacements
    )
    message = f"""
# Deck strategy
{deck_strategy}

# Card to replace
{card_to_replace.quantity}x {card_to_replace.card.name}
## Details
Role: {card_to_replace.role}
Importance: {card_to_replace.importance}
Tags: {card_to_replace.card.tags}
## LLM Summary:
{card_to_replace.card.llm_summary}

# Potential replacements
{card_list}
"""
    response = await agent.run(message)
    return response.output
