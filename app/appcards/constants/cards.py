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

EVERGREEN_KEYWORDS = {
    "Deathtouch",
    "Defender",
    "Double Strike",
    "Enchant",
    "Equip",
    "First Strike",
    "Flash",
    "Flying",
    "Haste",
    "Lifelink",
    "Menace",
    "Protection",
    "Prowess",
    "Reach",
    "Trample",
    "Vigilance",
    "Ward",
    "Scry",
}

CURRENT_STANDARD_SET_CODES = {
    "FDN",
    "WOE",
    "LCI",
    "MKM",
    "OTJ",
    "BIG",
    "BLB",
    "DSK",
    "DFT",
    "TDM",
    "FIN",
    "EOE",
    "SPM",
}

HIERARCHICAL_TAGS = {
    "Aggro": {
        "Weenie": "Low-cost, efficiently statted creatures intended to apply early combat pressure.",
        "GoWide": "Cards that generate or support multiple small creatures to overwhelm opponents through board presence.",
        "Burn": "Direct damage effects primarily aimed at reducing an opponent’s life total.",
        "Voltron": "Cards that concentrate power or protection onto a single primary threat to win through combat.",
        "Tempo": "Cards that gain advantage by disrupting the opponent while advancing your board efficiently.",
    },
    "Midrange": {
        "ValueThreat": "Creatures or permanents that provide strong standalone value while also applying pressure.",
        "ETBValue": "Cards that generate value immediately when entering the battlefield.",
        "Grindy": "Cards that provide incremental long-term advantage in extended games.",
        "Toolbox": "Cards that enable flexible answers or silver-bullet style solutions.",
    },
    "Control": {
        "Permission": "Cards that prevent opposing spells or actions from resolving.",
        "BoardControl": "Cards that manage or suppress the opponent’s board development.",
        "Removal": "Flexible answers that eliminate individual opposing threats.",
        "Prison": "Cards that restrict opponents’ actions or limit available resources over time.",
        "Pillowfort": "Defensive effects that discourage or tax opponents from attacking you.",
    },
    "Combo": {
        "ComboPiece": "A card that forms part of a synergistic interaction that can generate a powerful or game-winning effect.",
        "InfiniteCombo": "Cards that enable or complete a loop producing unlimited resources or deterministic victory.",
        "AlternateWincon": "Cards that win the game through non-standard victory conditions.",
        "Storm": "Cards that scale significantly with the number of spells cast in a turn.",
        "GraveyardCombo": "Cards that rely on graveyard interactions to assemble powerful synergies.",
        "Aristocrats": "Cards that benefit from sacrificing creatures or exploiting death triggers.",
    },
    "Ramp": {
        "LandRamp": "Effects that accelerate mana by putting additional lands into play.",
        "ManaDork": "Creatures that produce mana to accelerate development.",
        "ManaRock": "Non-creature permanents that generate mana.",
        "Ritual": "Temporary bursts of mana that provide short-term acceleration.",
        "CostReduction": "Cards that reduce the mana cost of spells or abilities.",
    },
    "CardAdvantage": {
        "DrawEngine": "Repeatable or high-yield effects that generate sustained card advantage.",
        "Cantrip": "Low-cost spells that replace themselves immediately.",
        "Looting": "Effects that draw and discard to improve card selection.",
        "Wheel": "Effects that cause players to discard hands and draw new ones.",
        "Tutor": "Cards that search the library for specific cards.",
        "Recursion": "Effects that return cards from the graveyard to hand, battlefield, or library.",
        "SelfMill": "Cards that intentionally put cards from your library into your graveyard.",
    },
    "Interaction": {
        "SpotRemoval": "Single-target answers to creatures or other permanents.",
        "BoardWipe": "Effects that remove multiple permanents at once.",
        "Counterspell": "Spells that directly counter other spells on the stack.",
        "Discard": "Effects that force opponents to discard cards from hand.",
        "GraveyardHate": "Cards that disrupt or neutralize graveyard-based strategies.",
        "ArtifactEnchantmentRemoval": "Effects that specifically answer artifacts or enchantments.",
    },
    "ResourceDenial": {
        "LandDestruction": "Cards that destroy, exile, or otherwise remove lands.",
        "TaxEffect": "Effects that increase opponents’ costs for spells or actions.",
        "StaxPiece": "Permanents that symmetrically restrict resources but are built around for advantage.",
    },
    "Synergy": {
        "TokenSynergy": "Cards that create tokens or scale in power based on token presence.",
        "SacrificeOutlet": "Cards that allow repeated or reliable sacrificing of permanents.",
        "Blink": "Effects that exile and return permanents to reuse enter-the-battlefield abilities.",
        "CopyEffect": "Cards that copy spells, abilities, or permanents.",
        "CheatIntoPlay": "Effects that put high-cost cards onto the battlefield without paying full cost.",
        "SpellsMatter": "Cards that reward casting noncreature spells.",
        "LifegainSynergy": "Cards that scale or trigger based on gaining life.",
    },
    "Tribal": {
        "TribalPayoff": "Cards that reward controlling multiple creatures of a shared type.",
        "TribalEnabler": "Cards that support or enhance a specific creature type strategy.",
    },
}

PRIMARY_TAG_DESCRIPTIONS = {
    "Aggro": "Cards that are designed to be aggressive and apply early pressure to opponents, often at the cost of long-term value or resilience.",
    "Midrange": "Cards that are effective in the mid-game, often balancing cost and power to adapt to various strategies.",
    "Control": "Cards that are designed to manage the game state and neutralise threats, often through disruption or resource denial.",
    "Combo": "Cards that are designed to work together in a synergistic way to create a powerful effect that can often win the game outright.",
    "Ramp": "Cards that accelerate mana production to enable casting more powerful spells earlier than normal.",
    "CardAdvantage": "Cards that provide additional resources or options, often by drawing extra cards or generating other forms of advantage.",
    "Interaction": "Cards that directly interact with opponents’ spells, abilities, or permanents to disrupt their plans.",
    "ResourceDenial": "Cards that restrict opponents’ access to resources like mana, cards, or actions.",
    "Synergy": "Cards that have enhanced value when combined with specific other cards or strategies.",
    "Tribal": "Cards that have enhanced value when combined with specific creature types or tribal synergies.",
}


@lru_cache(maxsize=1)
def _get_flat_card_tags() -> dict[str, str]:
    flat_tags = {}
    for primary_tag, subtags in HIERARCHICAL_TAGS.items():
        flat_tags[primary_tag] = PRIMARY_TAG_DESCRIPTIONS[primary_tag]
        for subtag, description in subtags.items():
            flat_tags[subtag] = description
    return flat_tags


CARD_TAGS = _get_flat_card_tags()

CARD_ROLES = {
    "WinCon": "Cards that are central to the deck’s strategy and often the main source of its power or win condition.",
    "Primary Engine": "Cards that are central to the deck’s strategy and often the main source of its power.",
    "Interaction": "Cards that are primarily included to interact with opponents’ strategies, such as removal, counterspells, or disruption.",
    "Ramp & Card Advantage": "Cards that are included to accelerate the deck’s mana production and card draw, enabling it to cast more powerful spells earlier than normal, or to provide additional resources or options.",
    "Support": "Cards that provide utility or support to the deck’s main strategy, but are not the primary source of power or interaction.",
    "Flex & filler": "Cards that can serve multiple roles or are included for versatility, often filling gaps in the deck or providing situational utility.",
    "Land": "Basic or non-basic lands that provide the mana base for the deck.",
}

CARD_IMPORTANCES = {
    "Critical": "Cards that are essential to the deck’s strategy and often the main source of its power or win condition. These cards are typically irreplaceable and central to the deck’s identity.",
    "High Synergy": "Cards that have strong interactions with other cards in the deck, significantly enhancing the deck’s overall strategy and performance. While they may not be strictly essential, their presence greatly increases the deck’s effectiveness.",
    "Functional": "Cards that serve a specific purpose in the deck and contribute to its overall strategy, but are not as central or impactful as Critical or High Synergy cards. These cards are often included for consistency, utility, or to fill specific roles within the deck.",
    "Generic": "Cards that are generally useful and can fit into a variety of decks, but do not have strong synergies with the specific cards in the deck. These cards are often included for their standalone value or versatility, rather than for their interactions with other cards in the deck.",
}
