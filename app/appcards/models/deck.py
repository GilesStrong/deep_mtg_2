from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from appcore.modules.beartype import beartype
from appuser.models.user import User
from django.core.exceptions import ValidationError
from django.db import models
from pydantic import BaseModel, Field

from appcards.models.card import Card

MAX_DECK_NAME_LENGTH = 64
SUMMARY_LENGTH_LIMIT = (50, 3000)
SHORT_SUMMARY_LENGTH_LIMIT = (10, 100)


class DeckCard(models.Model):
    """Through model to track card quantities in a deck"""

    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    deck = models.ForeignKey('Deck', on_delete=models.CASCADE, related_name='deckcard_set')
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    role = models.CharField(max_length=32, blank=True, null=True)
    importance = models.CharField(max_length=32, blank=True, null=True)
    replacement_cards = models.ManyToManyField(Card, related_name='replacement_for', blank=True)

    class Meta:
        unique_together = ('deck', 'card')

    def __str__(self) -> str:
        return f"{self.quantity}x {self.card.name} in {self.deck.name}"


@beartype
def _validate_set_str(value: list[str]) -> None:
    if len(value) != len(set(value)):
        raise ValidationError("Set codes must be unique.")


@beartype
def _validate_list_str(value: list[str]) -> None:
    """Empty logic: beartype validator to ensure a list of strings does not contain any non-string values."""
    pass


class Deck(models.Model):
    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    name = models.CharField(max_length=MAX_DECK_NAME_LENGTH, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cards = models.ManyToManyField(Card, through=DeckCard, related_name='decks')
    set_codes = models.JSONField(default=list, blank=True, validators=[_validate_set_str])
    short_llm_summary = models.TextField(blank=True, null=True, max_length=SHORT_SUMMARY_LENGTH_LIMIT[1])
    llm_summary = models.TextField(blank=True, null=True, max_length=SUMMARY_LENGTH_LIMIT[1])
    generation_history = models.JSONField(default=list, blank=True, validators=[_validate_list_str])
    tags = models.JSONField(default=list, blank=True, validators=[_validate_list_str])
    valid = models.BooleanField(default=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_decks",
    )

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.name:
            raise ValidationError("Deck name cannot be empty.")

        # Only validate and update set codes if the deck has already been saved (i.e. has a primary key), to avoid unnecessary queries when creating a new deck that doesn't have any cards yet.
        if self.pk:
            # Use a single query with prefetch_related to get all cards and their printings
            deck_cards = DeckCard.objects.filter(deck=self).select_related('card').prefetch_related('card__printings')

            set_codes = set()
            for deck_card in deck_cards:
                set_codes.update(deck_card.card.printings.values_list('set_code', flat=True))

            self.set_codes = list(set_codes)
            self.valid = validate_deck_basic(self).valid
        super().save(*args, **kwargs)

    if TYPE_CHECKING:
        from django.db.models.manager import RelatedManager

        deckcard_set: RelatedManager["DeckCard"]

    def update_validity(self) -> None:
        self.valid = validate_deck_basic(self).valid
        self.save()


class DeckValidationResult(BaseModel):
    valid: bool = Field(..., description="Whether the deck is valid according to basic rules")
    issues: list[str] = Field(default_factory=list, description="A list of issues found with the deck, if any")
    total_cards: int = Field(..., description="The total number of cards in the deck")


@beartype
def validate_deck_basic(deck_id: UUID | Deck) -> DeckValidationResult:
    """
    Validates a deck against basic rules (e.g. minimum 60 cards, no more than 4 copies of a card except basic lands).
    This function is intended to be used as a quick check for deck validity, and does not enforce any format-specific rules (e.g. Standard legality, Commander rules, etc.).
    It does not check for card legality based on set codes or banned/restricted lists, only the basic structural rules of deck construction.
    It also does not check for any specific card requirements, limitations, or allowances that may exist.

    Args:
        deck_id (UUID): The ID of the deck to validate.

    Returns:
        DeckValidationResult: An object indicating whether the deck is valid, any issues found, and the total number of cards in the deck.
    """

    if isinstance(deck_id, UUID):
        try:
            deck = Deck.objects.get(id=deck_id)
        except Deck.DoesNotExist:
            return DeckValidationResult(valid=False, issues=["Deck does not exist"], total_cards=0)
    else:
        deck = deck_id

    issues = []
    deck_cards = DeckCard.objects.filter(deck=deck).select_related('card')
    total_cards = deck_cards.aggregate(models.Sum('quantity'))['quantity__sum'] or 0
    if total_cards < 60:
        issues.append(f"Deck '{deck.name}' is invalid: it has only {total_cards} cards (minimum is 60).")
    for dc in deck_cards:
        if dc.quantity > 4 and (
            'Basic' not in dc.card.supertypes and 'deck can have any number of cards named' not in dc.card.text.lower()
        ):
            issues.append(f"{dc.quantity} copies of '{dc.card.name}' (ID: {dc.card.id})")
    if len(issues) > 0:
        return DeckValidationResult(valid=False, issues=issues, total_cards=total_cards)
    return DeckValidationResult(valid=True, issues=[], total_cards=total_cards)


class DailyDeckTheme(models.Model):
    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    date = models.DateField(auto_now_add=True)
    theme = models.TextField(max_length=255)

    def __str__(self) -> str:
        return f"{self.date}: {self.theme}"
