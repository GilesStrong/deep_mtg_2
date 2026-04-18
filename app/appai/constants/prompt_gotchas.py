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
Memories are shared across all agents and users, so they can be used to store general knowledge about card synergies, strategies, and other insights that can be useful for deck construction.
Do not use them to store information that is specific to the user's preferences or requirements, as this could lead to confusion and unintended consequences if that information is later retrieved in a different context.
The memory collection will grow over time, use it wisely and do not store information that is easily accessible through other means, such as card details that can be retrieved with the inspect_card tool, or information about the current state of the deck that can be retrieved with the list_deck_cards tool.
Instead use it to store insights and knowledge that can only be gained as you understand the current state of the meta, and the current legal cards in the format.
"""
