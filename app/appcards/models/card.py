from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from appcore.modules.beartype import beartype
from django.core.exceptions import ValidationError
from django.db import models


class Rarity(models.TextChoices):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    MYTHIC = "mythic"


class TypeEnum(StrEnum):
    ARTIFACT = "Artifact"
    CREATURE = "Creature"
    ENCHANTMENT = "Enchantment"
    INSTANT = "Instant"
    LAND = "Land"
    PLANESWALKER = "Planeswalker"
    SORCERY = "Sorcery"
    KINDRED = "Kindred"


class ManaColorEnum(StrEnum):
    RED = "R"
    BLUE = "U"
    GREEN = "G"
    WHITE = "W"
    BLACK = "B"
    COLORLESS = "C"


@beartype
def _validate_str_list(value: list[str]) -> None:
    pass


@beartype
def _validate_type_list(value: list[str]) -> None:
    for v in value:
        if v not in TypeEnum._value2member_map_:
            raise ValidationError(f"Invalid type: {v}")


@beartype
def _validate_mana_color_list(value: list[str]) -> None:
    for v in value:
        if v not in ManaColorEnum._value2member_map_:
            raise ValidationError(f"Invalid mana color: {v}")


class Card(models.Model):
    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    name = models.CharField(max_length=255, unique=True, editable=False)
    text = models.TextField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    llm_summary = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, validators=[_validate_str_list])
    subtypes = models.JSONField(default=list, blank=True, validators=[_validate_str_list])
    supertypes = models.JSONField(default=list, blank=True, validators=[_validate_str_list])
    power = models.CharField(max_length=10, blank=True, null=True)
    toughness = models.CharField(max_length=10, blank=True, null=True)
    mana_cost_red = models.IntegerField(default=0)
    mana_cost_blue = models.IntegerField(default=0)
    mana_cost_green = models.IntegerField(default=0)
    mana_cost_white = models.IntegerField(default=0)
    mana_cost_black = models.IntegerField(default=0)
    mana_cost_colorless = models.IntegerField(default=0)
    converted_mana_cost = models.IntegerField(default=0)
    colors = models.JSONField(default=list, blank=True, validators=[_validate_mana_color_list])
    types = models.JSONField(default=list, blank=True, validators=[_validate_type_list])
    rarity = models.CharField(
        max_length=10,
        choices=Rarity.choices,
        blank=False,
        null=False,
    )
    keywords = models.JSONField(default=list, blank=True, validators=[_validate_str_list])

    def __str__(self) -> str:
        return self.name

    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager

        from appcards.models.printing import Printing

        printings: RelatedManager["Printing"]
