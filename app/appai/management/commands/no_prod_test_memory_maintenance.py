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

import asyncio
from typing import Any

from app.settings import IS_DEPLOY_ENV
from django.core.management.base import BaseCommand

from appai.models.memory import Memory
from appai.services.graphs.memory_maintenance import run_memory_maintenance

example_memories = [
    {
        "text": "Pair Blood Artist with cheap sacrifice outlets to turn repeated creature deaths into a slow drain win condition.",
        "type": "combo",
        "cluster_id": "cluster_001",
    },
    {
        "text": "Zulaport Cutthroat gets much stronger when the deck has free sacrifice outlets and many disposable tokens.",
        "type": "combo",
        "cluster_id": "cluster_001",
    },
    {
        "text": "Bastion of Remembrance can act as a redundant Blood Artist effect in aristocrats shells that sacrifice creatures repeatedly.",
        "type": "combo",
        "cluster_id": "cluster_001",
    },
    {
        "text": "Aristocrats decks should value token makers highly because every expendable creature becomes extra damage with drain effects.",
        "type": "archetype_hint",
        "cluster_id": "cluster_001",
    },
    {
        "text": "When building sacrifice decks, include multiple death-trigger payoffs so the deck still functions if one Blood Artist effect is removed.",
        "type": "archetype_hint",
        "cluster_id": "cluster_001",
    },
    {
        "text": "Collected Company wants a high density of creatures costing three or less to maximize hit rate.",
        "type": "deckbuilding",
        "cluster_id": "cluster_002",
    },
    {
        "text": "Chord of Calling works best in creature-heavy shells that can convoke with mana dorks and tokens.",
        "type": "deckbuilding",
        "cluster_id": "cluster_002",
    },
    {
        "text": "Creature toolbox decks should avoid too many noncreature spells if they rely on Collected Company for card advantage.",
        "type": "deckbuilding",
        "cluster_id": "cluster_002",
    },
    {
        "text": "A Company deck should usually keep most silver bullets as creatures rather than artifacts or enchantments.",
        "type": "archetype_hint",
        "cluster_id": "cluster_002",
    },
    {
        "text": "If a deck uses both Collected Company and Eldritch Evolution, prioritize creatures that are useful when hit naturally and when tutored.",
        "type": "deckbuilding",
        "cluster_id": "cluster_002",
    },
    {
        "text": "Graveyard decks need protection against Rest in Peace because it shuts off recursion, delve, escape, and reanimation lines.",
        "type": "meta_threat",
        "cluster_id": "cluster_003",
    },
    {
        "text": "Leyline of the Void is a major problem for graveyard-based strategies and should be answered before committing resources.",
        "type": "meta_threat",
        "cluster_id": "cluster_003",
    },
    {
        "text": "Unlicensed Hearse pressures graveyard decks while also becoming a large threat, so artifact removal is important after sideboard.",
        "type": "sideboard",
        "cluster_id": "cluster_003",
    },
    {
        "text": "Decks relying on Kroxa, Uro, or escape cards should bring in answers to permanent-based graveyard hate.",
        "type": "sideboard",
        "cluster_id": "cluster_003",
    },
    {
        "text": "Reanimator strategies need a plan for one-shot graveyard hate like Soul-Guide Lantern as well as static hate like Rest in Peace.",
        "type": "sideboard",
        "cluster_id": "cluster_003",
    },
    {
        "text": "Against control decks, avoid overextending into sweepers unless you can rebuild quickly.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_004",
    },
    {
        "text": "When facing Supreme Verdict, hold back enough threats to keep pressure after the board is cleared.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_004",
    },
    {
        "text": "Creature decks should sequence threats so a single Wrath of God does not remove the entire game plan.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_004",
    },
    {
        "text": "If the opponent represents a sweeper, commit only enough power to force them to answer the board.",
        "type": "matchup",
        "cluster_id": "cluster_004",
    },
    {
        "text": "Aggro decks can beat control by forcing awkward sweeper timing and keeping haste or manland threats in reserve.",
        "type": "matchup",
        "cluster_id": "cluster_004",
    },
    {
        "text": "Rakdos midrange wants efficient discard, cheap removal, and sticky threats to trade resources profitably.",
        "type": "archetype_hint",
        "cluster_id": "cluster_005",
    },
    {
        "text": "Thoughtseize plus Fatal Push supports a Rakdos plan of disrupting the opponent before deploying value creatures.",
        "type": "archetype_hint",
        "cluster_id": "cluster_005",
    },
    {
        "text": "Fable of the Mirror-Breaker is excellent in Rakdos shells because it filters cards and creates multiple bodies over time.",
        "type": "card_evaluation",
        "cluster_id": "cluster_005",
    },
    {
        "text": "Bloodtithe Harvester fits Rakdos midrange by pressuring early and later turning into removal.",
        "type": "card_evaluation",
        "cluster_id": "cluster_005",
    },
    {
        "text": "Rakdos decks should balance discard and removal so they do not draw dead cards against creature-light or creature-heavy opponents.",
        "type": "deckbuilding",
        "cluster_id": "cluster_005",
    },
    {
        "text": "Mono-red aggro should prioritize one-mana threats and burn spells that can target both creatures and players.",
        "type": "archetype_hint",
        "cluster_id": "cluster_006",
    },
    {
        "text": "Lightning Bolt-style effects are especially valuable in red aggro because they clear blockers or finish the opponent.",
        "type": "card_evaluation",
        "cluster_id": "cluster_006",
    },
    {
        "text": "Red aggressive decks usually want a low curve to spend all mana every turn and punish slow starts.",
        "type": "deckbuilding",
        "cluster_id": "cluster_006",
    },
    {
        "text": "In burn-heavy red decks, avoid too many expensive cards because they reduce the chance of double-spelling early.",
        "type": "deckbuilding",
        "cluster_id": "cluster_006",
    },
    {
        "text": "Against lifegain decks, mono-red should sideboard anti-lifegain effects or shift toward more persistent threats.",
        "type": "sideboard",
        "cluster_id": "cluster_006",
    },
    {
        "text": "Azorius control needs a mix of counterspells, sweepers, spot removal, and card draw to cover different threat types.",
        "type": "archetype_hint",
        "cluster_id": "cluster_007",
    },
    {
        "text": "Control decks should avoid loading up only on counterspells because resolved creatures can become difficult to answer.",
        "type": "deckbuilding",
        "cluster_id": "cluster_007",
    },
    {
        "text": "Teferi-style planeswalkers are strong in control because they generate advantage while forcing the opponent to attack awkwardly.",
        "type": "card_evaluation",
        "cluster_id": "cluster_007",
    },
    {
        "text": "Azorius control should include instant-speed card draw to keep mana open for counters before committing resources.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_007",
    },
    {
        "text": "Against fast aggro, control decks need early interaction more than expensive card advantage spells.",
        "type": "matchup",
        "cluster_id": "cluster_007",
    },
    {
        "text": "Green ramp decks should use early mana acceleration to cast oversized threats ahead of schedule.",
        "type": "archetype_hint",
        "cluster_id": "cluster_008",
    },
    {
        "text": "Llanowar Elves and similar mana creatures are strongest when the deck has powerful three- and four-mana follow-ups.",
        "type": "card_evaluation",
        "cluster_id": "cluster_008",
    },
    {
        "text": "Ramp strategies should include payoff cards that stabilize the board, not just cards that are expensive.",
        "type": "deckbuilding",
        "cluster_id": "cluster_008",
    },
    {
        "text": "Cultivate-style ramp is better in slower formats where spending turn three without affecting combat is acceptable.",
        "type": "card_evaluation",
        "cluster_id": "cluster_008",
    },
    {
        "text": "Mana dork decks are vulnerable to cheap removal, so they should still function if the first accelerator dies.",
        "type": "meta_threat",
        "cluster_id": "cluster_008",
    },
    {
        "text": "Izzet spells decks want cheap cantrips to trigger prowess, fill the graveyard, and smooth draws.",
        "type": "archetype_hint",
        "cluster_id": "cluster_009",
    },
    {
        "text": "Monastery Swiftspear becomes much stronger when the deck has many one-mana spells to chain in a single turn.",
        "type": "combo",
        "cluster_id": "cluster_009",
    },
    {
        "text": "Sprite Dragon rewards the same low-cost spell density as prowess creatures but scales permanently over time.",
        "type": "card_evaluation",
        "cluster_id": "cluster_009",
    },
    {
        "text": "Spells-matter decks should keep creature count low but include enough threats to avoid drawing only cantrips and burn.",
        "type": "deckbuilding",
        "cluster_id": "cluster_009",
    },
    {
        "text": "Against removal-heavy decks, Izzet prowess should avoid committing all threats before protecting or immediately pumping them.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_009",
    },
    {
        "text": "Blink decks can reuse enter-the-battlefield triggers for incremental value.",
        "type": "combo",
        "cluster_id": "cluster_010",
    },
    {
        "text": "Ephemerate is strongest with creatures that draw cards, remove permanents, or create mana when they enter.",
        "type": "combo",
        "cluster_id": "cluster_010",
    },
    {
        "text": "Flickerwisp-style effects can reset opposing permanents or reuse friendly ETB creatures depending on board state.",
        "type": "card_evaluation",
        "cluster_id": "cluster_010",
    },
    {
        "text": "Yorion shells should include enough ETB permanents that blinking the board generates immediate advantage.",
        "type": "archetype_hint",
        "cluster_id": "cluster_010",
    },
    {
        "text": "Blink strategies should not rely only on the blink spell; the creatures need to be acceptable when played normally.",
        "type": "deckbuilding",
        "cluster_id": "cluster_010",
    },
    {
        "text": "Artifact decks benefit from cheap artifacts that replace themselves or provide mana acceleration.",
        "type": "archetype_hint",
        "cluster_id": "cluster_011",
    },
    {
        "text": "Emry, Lurker of the Loch is powerful when the deck has many low-cost artifacts to mill and replay.",
        "type": "combo",
        "cluster_id": "cluster_011",
    },
    {
        "text": "Urza-style artifact shells want artifacts that are useful before and after they become mana sources.",
        "type": "deckbuilding",
        "cluster_id": "cluster_011",
    },
    {
        "text": "Thought Monitor rewards high artifact density and can refuel affinity-style decks after emptying the hand.",
        "type": "card_evaluation",
        "cluster_id": "cluster_011",
    },
    {
        "text": "Artifact strategies should prepare for Stony Silence and Force of Vigor because both can disrupt their core engine.",
        "type": "sideboard",
        "cluster_id": "cluster_011",
    },
    {
        "text": "Enchantress decks need many enchantments that replace themselves to keep the draw engine running.",
        "type": "archetype_hint",
        "cluster_id": "cluster_012",
    },
    {
        "text": "Sythis, Harvest's Hand turns cheap enchantments into a steady stream of cards and life.",
        "type": "combo",
        "cluster_id": "cluster_012",
    },
    {
        "text": "Enchantress shells should prioritize low-cost enchantments so they can chain multiple spells after resolving a payoff.",
        "type": "deckbuilding",
        "cluster_id": "cluster_012",
    },
    {
        "text": "Sterling Grove-style protection is useful because enchantress engines often depend on fragile key permanents.",
        "type": "sideboard",
        "cluster_id": "cluster_012",
    },
    {
        "text": "Against enchantment removal, enchantress decks should diversify payoffs rather than relying on only one draw engine.",
        "type": "meta_threat",
        "cluster_id": "cluster_012",
    },
    {
        "text": "Reanimator decks should combine discard outlets, reanimation spells, and high-impact creatures in consistent proportions.",
        "type": "archetype_hint",
        "cluster_id": "cluster_013",
    },
    {
        "text": "Entomb effects are strongest when they can find different reanimation targets for different matchups.",
        "type": "combo",
        "cluster_id": "cluster_013",
    },
    {
        "text": "Faithless Looting-style cards support reanimator by putting large creatures into the graveyard while digging for reanimation spells.",
        "type": "combo",
        "cluster_id": "cluster_013",
    },
    {
        "text": "Reanimation targets should either win quickly, stabilize immediately, or protect themselves from common removal.",
        "type": "card_evaluation",
        "cluster_id": "cluster_013",
    },
    {
        "text": "Reanimator sideboards need backup plans because graveyard hate can make the main engine unreliable.",
        "type": "sideboard",
        "cluster_id": "cluster_013",
    },
    {
        "text": "Token decks scale well with anthem effects because each pump increases the damage of the entire board.",
        "type": "combo",
        "cluster_id": "cluster_014",
    },
    {
        "text": "Intangible Virtue is strongest when the deck consistently produces multiple creature tokens before combat.",
        "type": "card_evaluation",
        "cluster_id": "cluster_014",
    },
    {
        "text": "Go-wide token strategies should include protection against sweepers or ways to rebuild after a board wipe.",
        "type": "sideboard",
        "cluster_id": "cluster_014",
    },
    {
        "text": "Cards that create two or more bodies are better than single large threats in anthem-based token decks.",
        "type": "deckbuilding",
        "cluster_id": "cluster_014",
    },
    {
        "text": "Token decks can pressure planeswalkers efficiently because they spread power across many attackers.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_014",
    },
    {
        "text": "Mill decks should focus on efficient library depletion rather than trying to play a normal damage race.",
        "type": "archetype_hint",
        "cluster_id": "cluster_015",
    },
    {
        "text": "Archive Trap is strongest when opponents search their library, especially with fetch lands or tutor effects.",
        "type": "combo",
        "cluster_id": "cluster_015",
    },
    {
        "text": "Ruin Crab rewards repeated land drops and pairs well with fetch lands for multiple mill triggers in one turn.",
        "type": "combo",
        "cluster_id": "cluster_015",
    },
    {
        "text": "Mill strategies need removal for fast creatures because they often win on a different axis than combat.",
        "type": "deckbuilding",
        "cluster_id": "cluster_015",
    },
    {
        "text": "Against graveyard decks, mill can accidentally help the opponent, so sideboard graveyard hate may still be needed.",
        "type": "matchup",
        "cluster_id": "cluster_015",
    },
    {
        "text": "Lands-matter decks should include extra land drop effects to convert land-heavy draws into acceleration.",
        "type": "archetype_hint",
        "cluster_id": "cluster_016",
    },
    {
        "text": "Lotus Cobra is strongest with fetch lands or cards that put multiple lands onto the battlefield in one turn.",
        "type": "combo",
        "cluster_id": "cluster_016",
    },
    {
        "text": "Landfall creatures need enough lands and fetch effects to trigger reliably during combat turns.",
        "type": "deckbuilding",
        "cluster_id": "cluster_016",
    },
    {
        "text": "Scapeshift-style decks should count their lands carefully because the combo often depends on reaching a precise threshold.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_016",
    },
    {
        "text": "Lands decks are vulnerable to Blood Moon effects, so they need basics or enchantment removal after sideboard.",
        "type": "sideboard",
        "cluster_id": "cluster_016",
    },
    {
        "text": "Poison decks win by accumulating ten poison counters, so pump and protection spells can be equivalent to burn spells.",
        "type": "archetype_hint",
        "cluster_id": "cluster_017",
    },
    {
        "text": "Infect creatures are dangerous because a single unblocked attacker can become lethal with enough pump spells.",
        "type": "combo",
        "cluster_id": "cluster_017",
    },
    {
        "text": "Protection spells are crucial in poison strategies because losing the infect creature often strands pump spells in hand.",
        "type": "deckbuilding",
        "cluster_id": "cluster_017",
    },
    {
        "text": "Against poison decks, instant-speed removal should be saved for the turn they commit pump spells.",
        "type": "matchup",
        "cluster_id": "cluster_017",
    },
    {
        "text": "Cheap blockers and removal are important against toxic or infect decks because early poison counters are difficult to undo.",
        "type": "meta_threat",
        "cluster_id": "cluster_017",
    },
    {
        "text": "Tribal decks should maximize creature type density so lord effects consistently pump the whole board.",
        "type": "archetype_hint",
        "cluster_id": "cluster_018",
    },
    {
        "text": "Merfolk lords become much stronger when most creatures in the deck share the Merfolk type.",
        "type": "combo",
        "cluster_id": "cluster_018",
    },
    {
        "text": "Elves decks rely on many cheap Elves because their mana engines and payoff cards count creature type density.",
        "type": "archetype_hint",
        "cluster_id": "cluster_018",
    },
    {
        "text": "Goblin tribal decks should balance lords, token makers, and sacrifice or haste payoffs to avoid drawing only support cards.",
        "type": "deckbuilding",
        "cluster_id": "cluster_018",
    },
    {
        "text": "Tribal strategies are vulnerable to sweepers because they often need several creatures in play for synergy bonuses.",
        "type": "meta_threat",
        "cluster_id": "cluster_018",
    },
    {
        "text": "Combo decks should include card selection to find missing pieces without diluting the core engine too much.",
        "type": "deckbuilding",
        "cluster_id": "cluster_019",
    },
    {
        "text": "Two-card combos are stronger when each piece has some standalone utility outside the combo turn.",
        "type": "card_evaluation",
        "cluster_id": "cluster_019",
    },
    {
        "text": "Tutors improve combo consistency but can make the deck more vulnerable to discard and hate cards.",
        "type": "deckbuilding",
        "cluster_id": "cluster_019",
    },
    {
        "text": "When piloting combo, avoid exposing a key piece before the turn it can generate value or win immediately.",
        "type": "gameplay_pattern",
        "cluster_id": "cluster_019",
    },
    {
        "text": "Sideboards against combo should include disruption that attacks the combo axis rather than generic creature removal.",
        "type": "sideboard",
        "cluster_id": "cluster_019",
    },
    {
        "text": "Mana bases for three-color decks should prioritize untapped sources for early interaction.",
        "type": "mana_base",
        "cluster_id": "cluster_020",
    },
    {
        "text": "Aggressive multicolor decks cannot afford too many tapped lands because they need to curve out from turn one.",
        "type": "mana_base",
        "cluster_id": "cluster_020",
    },
    {
        "text": "Control decks can accept more tapped dual lands than aggro decks if the early interaction suite remains castable.",
        "type": "mana_base",
        "cluster_id": "cluster_020",
    },
    {
        "text": "Decks with double-colored spells need enough sources of that color by the turn those spells are intended to be cast.",
        "type": "mana_base",
        "cluster_id": "cluster_020",
    },
    {
        "text": "Fetch-shock mana bases are flexible but require life total management against burn and fast aggro.",
        "type": "mana_base",
        "cluster_id": "cluster_020",
    },
]


class Command(BaseCommand):
    help = 'Test memory maintenance. Do not run this in production as it creates test memories'

    def handle(self, *args: Any, **options: Any) -> None:
        if IS_DEPLOY_ENV:
            print(
                "This command should not be run in production because it creates test memories. Exiting without doing anything."
            )
            return
        memories = []
        for i, memory in enumerate(example_memories):
            memories.append(
                Memory(
                    name=f"Test Memory {i}",
                    text=memory["text"],
                )
            )
        Memory.objects.bulk_create(memories)
        print(f"Created {len(memories)} test memories. Running memory maintenance...")
        print(Memory.objects.count(), "memories before maintenance.")
        asyncio.run(run_memory_maintenance())
        print(Memory.objects.count(), "memories after maintenance.")
