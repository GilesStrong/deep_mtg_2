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

from appai.models.deck_build import DeckBuildStatus

POLLABLE_BUILD_STATUSES: tuple[str, ...] = (
    str(DeckBuildStatus.PENDING),
    str(DeckBuildStatus.IN_PROGRESS),
    str(DeckBuildStatus.BUILDING_DECK),
    str(DeckBuildStatus.CLASSIFYING_DECK_CARDS),
    str(DeckBuildStatus.FINDING_REPLACEMENT_CARDS),
)


def is_pollable_build_status(status: str) -> bool:
    """Return whether a deck build status is pollable (actively in progress).

    Args:
        status (str): The deck build status value to evaluate.

    Returns:
        bool: True if the status is in the pollable in-progress set; otherwise False.
    """
    return status in POLLABLE_BUILD_STATUSES
