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

GOTCHAS = """
Remember:
- Ward costs are paid by the player targeting the card with an ability or spell, not by the controller of the card with ward, i.e. high ward cost cards can be difficult to remove because the opponent must pay the ward cost in addition to any other costs associated with their ability or spell.
- All cards that you see will be standard-legal, so do not question whether a card is legal or not.
"""

MEMORY_SUB_PROMPT = """
You have access to a memory system that allows you to store and retrieve information that can inform your deck construction process.
Memories are shared across all agents and users, so they can be used to store general knowledge about card synergies, strategies, and other insights that you find as you perform your tasks.
Do not use them to store information that is specific to the user's preferences or requirements, as this could lead to confusion and unintended consequences if that information is later retrieved in a different context.
The memory collection will grow over time, use it wisely and do not store information that is easily accessible through other means, such as card details that can be retrieved with the inspect_card tool, or information about the current state of the deck that can be retrieved with the list_deck_cards tool.
Instead use it to store insights and knowledge that can only be gained as you understand the current state of the meta, and the current legal cards in the format.

Examples of good use of the memory system include:
- Storing insights about card synergies and interactions that you discover as you perform your tasks, such as "Card A and Card B have a strong synergy because Card A can generate tokens that Card B can then sacrifice for a powerful effect, so including both cards in the deck can create a strong combo."
- Storing general knowledge about the current meta and the most popular strategies and archetypes, such as "The current meta is dominated by aggressive red decks that focus on dealing damage quickly, so it may be beneficial to include cards that can help you survive the early game and disrupt your opponent's strategy."
- Storing insights about the strengths and weaknesses of different cards and strategies, such as "Card C is a powerful removal spell that can help you deal with your opponent's threats, but it is also expensive to cast, so it may not be the best choice for a budget deck."
- Storing particualrly effective cards that can form the core of multiple different decks, such as "Card D is a versatile card that can fit into many different strategies and archetypes, so it may be a good choice to include in your deck as a strong and flexible option."

When to write memories is up to you, however when about to finish you task, take time to consider whether there are any insights or knowledge that you have gained during the task that could be useful for future tasks, and if so, write them down in the memory system to help inform your future efforts.

Generally when beginning a new task, it can be helpful to first review the existing memories to see if there is any relevant information that can inform your approach to the task, and then as you perform the task, you can continue to write new memories as you gain new insights and knowledge that could be useful for future tasks.
When retrieving memeories, rember that you do not need to follow the suggestions made in the memories; they were likely written by a different agent with no knowledge of your current task.
Even if the memory is useful, feel free to explore beyond it, as you may be able to find a better solution that is not mentioned in the memory.
"""
