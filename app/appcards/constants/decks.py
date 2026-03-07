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

from functools import lru_cache

from appcards.models.card import ManaColorEnum

GROUPED_DECK_CLASSIFICATIONS = {
    "Archetype": {
        "Aggro": "A proactive deck focused on winning quickly through early pressure.",
        "Midrange": "A flexible deck built around efficient threats and incremental value.",
        "Control": "A reactive deck that stabilizes before winning through inevitability.",
        "Combo": "A deck built to assemble synergistic interactions that produce a decisive win.",
        "Tempo": "A deck that disrupts opponents while applying efficient pressure.",
        "Prison": "A deck focused on restricting opponents’ ability to meaningfully play the game.",
        "Superfriends": "A deck built around planeswalkers as primary engines and win conditions.",
        "Reanimator": "A deck built around cheating large threats into play from the graveyard.",
        "Lands": "A deck that treats lands as its primary engine or win condition.",
        "Enchantress": "A deck built around enchantments as its core value engine.",
        "ArtifactsMatter": "A deck centered on artifacts as its primary synergy and engine.",
        "Aristocrats": "A deck built around sacrificing creatures for incremental advantage or lethal triggers.",
        "Tokens": "A deck built around generating and leveraging large numbers of creature tokens.",
        "Stompy": "A deck focused on deploying oversized threats ahead of curve.",
        "Spellslinger": "A deck centered around chaining noncreature spells for value or combo.",
        "Mill": "A deck that wins by emptying the opponent’s library.",
        "Burn": "A deck that primarily wins through direct non-combat damage.",
        "Infect": "A deck built around winning via poison counters.",
        "Voltron": "A deck focused on empowering a single primary threat to win via combat.",
        "Blink": "A deck built around repeatedly reusing enter-the-battlefield effects.",
        "Tribal": "A deck structured around a specific creature type as its core identity.",
    },
    "PrimaryWinCondition": {
        "CombatDamage": "Wins primarily through creature-based combat.",
        "DirectDamage": "Wins via non-combat damage to opponents.",
        "InfiniteCombo": "Wins through a deterministic or infinite interaction.",
        "AlternateWincon": "Wins through a non-standard victory condition.",
        "Attrition": "Wins by exhausting opponent resources over time.",
    },
    "Speed": {
        "Fast": "Designed to win in the early stages of the game.",
        "Medium": "Designed to establish advantage midgame.",
        "Slow": "Designed to dominate in long games.",
    },
    "ResourceAxis": {
        "RampFocused": "Relies heavily on accelerating mana development.",
        "CardAdvantageFocused": "Built around generating sustained card advantage.",
        "GraveyardFocused": "Uses the graveyard as a primary resource.",
        "SacrificeFocused": "Built around sacrificing permanents for value.",
        "SpellsMatter": "Focused on chaining or leveraging noncreature spells.",
        "TokenFocused": "Built around producing and leveraging tokens.",
    },
    "InteractionDensity": {
        "LowInteraction": "Minimal disruption; primarily proactive.",
        "ModerateInteraction": "Balanced between threats and answers.",
        "HighInteraction": "Heavy emphasis on disruption and control.",
    },
    "BoardStrategy": {
        "GoWide": "Overwhelms with multiple creatures.",
        "GoTall": "Focuses power into one or few threats.",
        "BoardControl": "Maintains dominance through board suppression.",
    },
    "ConsistencyProfile": {
        "TutorHeavy": "Relies significantly on library search for consistency.",
        "RedundantPieces": "Uses many similar effects to ensure reliability.",
        "HighVariance": "Relies on explosive but less consistent lines.",
    },
    "ColorIdentity": {
        "Colorless": "Deck contains no colored mana symbols in its color identity.",
        "MonoWhite": "Deck’s color identity is white only.",
        "MonoBlue": "Deck’s color identity is blue only.",
        "MonoBlack": "Deck’s color identity is black only.",
        "MonoRed": "Deck’s color identity is red only.",
        "MonoGreen": "Deck’s color identity is green only.",
        "Azorius": "White-Blue color identity.",
        "Dimir": "Blue-Black color identity.",
        "Rakdos": "Black-Red color identity.",
        "Gruul": "Red-Green color identity.",
        "Selesnya": "Green-White color identity.",
        "Orzhov": "White-Black color identity.",
        "Izzet": "Blue-Red color identity.",
        "Golgari": "Black-Green color identity.",
        "Boros": "Red-White color identity.",
        "Simic": "Green-Blue color identity.",
        "Esper": "White-Blue-Black color identity.",
        "Grixis": "Blue-Black-Red color identity.",
        "Jund": "Black-Red-Green color identity.",
        "Naya": "Red-Green-White color identity.",
        "Bant": "Green-White-Blue color identity.",
        "Abzan": "White-Black-Green color identity.",
        "Jeskai": "Blue-Red-White color identity.",
        "Sultai": "Black-Green-Blue color identity.",
        "Mardu": "Red-White-Black color identity.",
        "Temur": "Green-Blue-Red color identity.",
        "FourColorNonWhite": "Four colors excluding white.",
        "FourColorNonBlue": "Four colors excluding blue.",
        "FourColorNonBlack": "Four colors excluding black.",
        "FourColorNonRed": "Four colors excluding red.",
        "FourColorNonGreen": "Four colors excluding green.",
        "FiveColor": "Deck contains all five colors in its color identity.",
    },
}


@lru_cache(maxsize=1)
def _get_flat_deck_classifications() -> dict[str, str]:
    flat_dict = {}
    for category, classifications in GROUPED_DECK_CLASSIFICATIONS.items():
        for classification, description in classifications.items():
            flat_dict[classification] = description
    return flat_dict


DECK_CLASSIFICATIONS = _get_flat_deck_classifications()


COLOR_IDENTITY_TO_COLORS: dict[str, list[str]] = {
    "Colorless": [],
    "MonoWhite": [ManaColorEnum.WHITE.value],
    "MonoBlue": [ManaColorEnum.BLUE.value],
    "MonoBlack": [ManaColorEnum.BLACK.value],
    "MonoRed": [ManaColorEnum.RED.value],
    "MonoGreen": [ManaColorEnum.GREEN.value],
    "Azorius": [ManaColorEnum.WHITE.value, ManaColorEnum.BLUE.value],
    "Dimir": [ManaColorEnum.BLUE.value, ManaColorEnum.BLACK.value],
    "Rakdos": [ManaColorEnum.BLACK.value, ManaColorEnum.RED.value],
    "Gruul": [ManaColorEnum.RED.value, ManaColorEnum.GREEN.value],
    "Selesnya": [ManaColorEnum.GREEN.value, ManaColorEnum.WHITE.value],
    "Orzhov": [ManaColorEnum.WHITE.value, ManaColorEnum.BLACK.value],
    "Izzet": [ManaColorEnum.BLUE.value, ManaColorEnum.RED.value],
    "Golgari": [ManaColorEnum.BLACK.value, ManaColorEnum.GREEN.value],
    "Boros": [ManaColorEnum.RED.value, ManaColorEnum.WHITE.value],
    "Simic": [ManaColorEnum.GREEN.value, ManaColorEnum.BLUE.value],
    "Esper": [ManaColorEnum.WHITE.value, ManaColorEnum.BLUE.value, ManaColorEnum.BLACK.value],
    "Grixis": [ManaColorEnum.BLUE.value, ManaColorEnum.BLACK.value, ManaColorEnum.RED.value],
    "Jund": [ManaColorEnum.BLACK.value, ManaColorEnum.RED.value, ManaColorEnum.GREEN.value],
    "Naya": [ManaColorEnum.RED.value, ManaColorEnum.GREEN.value, ManaColorEnum.WHITE.value],
    "Bant": [ManaColorEnum.GREEN.value, ManaColorEnum.WHITE.value, ManaColorEnum.BLUE.value],
    "Abzan": [ManaColorEnum.WHITE.value, ManaColorEnum.BLACK.value, ManaColorEnum.GREEN.value],
    "Jeskai": [ManaColorEnum.BLUE.value, ManaColorEnum.RED.value, ManaColorEnum.WHITE.value],
    "Sultai": [ManaColorEnum.BLACK.value, ManaColorEnum.GREEN.value, ManaColorEnum.BLUE.value],
    "Mardu": [ManaColorEnum.RED.value, ManaColorEnum.WHITE.value, ManaColorEnum.BLACK.value],
    "Temur": [ManaColorEnum.GREEN.value, ManaColorEnum.BLUE.value, ManaColorEnum.RED.value],
    "FourColorNonWhite": [
        ManaColorEnum.BLUE.value,
        ManaColorEnum.BLACK.value,
        ManaColorEnum.RED.value,
        ManaColorEnum.GREEN.value,
    ],
    "FourColorNonBlue": [
        ManaColorEnum.WHITE.value,
        ManaColorEnum.BLACK.value,
        ManaColorEnum.RED.value,
        ManaColorEnum.GREEN.value,
    ],
    "FourColorNonBlack": [
        ManaColorEnum.WHITE.value,
        ManaColorEnum.BLUE.value,
        ManaColorEnum.RED.value,
        ManaColorEnum.GREEN.value,
    ],
    "FourColorNonRed": [
        ManaColorEnum.WHITE.value,
        ManaColorEnum.BLUE.value,
        ManaColorEnum.BLACK.value,
        ManaColorEnum.GREEN.value,
    ],
    "FourColorNonGreen": [
        ManaColorEnum.WHITE.value,
        ManaColorEnum.BLUE.value,
        ManaColorEnum.BLACK.value,
        ManaColorEnum.RED.value,
    ],
    "FiveColor": [
        ManaColorEnum.WHITE.value,
        ManaColorEnum.BLUE.value,
        ManaColorEnum.BLACK.value,
        ManaColorEnum.RED.value,
        ManaColorEnum.GREEN.value,
    ],
}
