from django.forms.models import model_to_dict
from pydantic import BaseModel

from appcards.models import Card


class CardInfo(BaseModel):
    name: str
    text: str
    subtypes: list[str]
    supertypes: list[str]
    power: str | None
    toughness: str | None
    mana_cost_red: int
    mana_cost_blue: int
    mana_cost_green: int
    mana_cost_white: int
    mana_cost_black: int
    mana_cost_colorless: int
    set_codes: list[str]


def card_to_info(card: Card) -> CardInfo:
    card_dict = model_to_dict(card, fields=[f.name for f in card._meta.fields])
    card_dict['set_codes'] = [p.set_code for p in card.printings.all()]
    return CardInfo(name=card.name, **card_dict)
