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

BUILD_DECK_CONTEXT = """
The tool being called by this route will launch a long-running process to automatically build a Magic: The Gathering deck for the user.
The user should be describing the kind of deck that they want to build, or how they want to refine an existing deck.
The request may be provided in a fun, or creative way, and provided it a a relevant build request, this alone is not ground for removal.
The tool cannot provide answers to the user, so it should not be used to ask questions, or make requests that are not related to building a deck.

Examples:
- "Build me a red aggro deck with lots of goblins and burn spells" -- RELEVANT
- "I want to build a control deck with blue and white cards, and lots of counter    spells" -- RELEVANT
- "What does haste do in MTG?" -- NOT RELEVANT (asking a question, not making a request)
- "Sometimes I dream about cheese" -- NOT RELEVANT (not related to building a deck)
- "I want to build a deck, but I don't know where to start" -- NOT RELEVANT (not providing any information about the kind of deck they want to build)
"""
