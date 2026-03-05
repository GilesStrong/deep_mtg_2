from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck, DeckCard
from appuser.models.user import User
from django.test import TestCase
from django.utils import timezone

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appai.tasks.cleanup import cleanup_old_deck_build_tasks

_MODULE = "appai.tasks.cleanup"
_FIXED_NOW = timezone.make_aware(datetime(2026, 3, 5, 12, 0, 0), timezone.get_current_timezone())


class CleanupOldDeckBuildTasksTests(TestCase):
    """Tests for the cleanup_old_deck_build_tasks Celery task."""

    def _create_user(self, suffix: str) -> User:
        """Create a test user.

        Args:
            suffix: Unique suffix used to generate a stable google_id.

        Returns:
            The created User instance.
        """
        return User.objects.create(google_id=f"cleanup-user-{suffix}")

    def _create_card(self, name: str) -> Card:
        """Create a minimal valid card for deck membership tests.

        Args:
            name: Card name.

        Returns:
            The created Card instance.
        """
        return Card.objects.create(
            name=name,
            text="Test rules text",
            rarity=Rarity.COMMON,
        )

    @patch(f"{_MODULE}.datetime")
    def test_marks_only_old_in_progress_tasks_failed(self, mock_datetime):
        """
        GIVEN deck build tasks with mixed statuses and ages
        WHEN cleanup_old_deck_build_tasks runs
        THEN only tasks in in-progress statuses older than 2 hours are marked FAILED
        """
        mock_datetime.now.return_value = _FIXED_NOW

        user = self._create_user("tasks")
        deck = Deck.objects.create(name="Cleanup Deck", user=user)

        stale_in_progress = DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.IN_PROGRESS)
        stale_building = DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.BUILDING_DECK)
        recent_in_progress = DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.IN_PROGRESS)
        stale_completed = DeckBuildTask.objects.create(deck=deck, status=DeckBuildStatus.COMPLETED)

        old_timestamp = _FIXED_NOW - timedelta(hours=3)
        recent_timestamp = _FIXED_NOW - timedelta(minutes=30)
        DeckBuildTask.objects.filter(id=stale_in_progress.id).update(updated_at=old_timestamp)
        DeckBuildTask.objects.filter(id=stale_building.id).update(updated_at=old_timestamp)
        DeckBuildTask.objects.filter(id=recent_in_progress.id).update(updated_at=recent_timestamp)
        DeckBuildTask.objects.filter(id=stale_completed.id).update(updated_at=old_timestamp)

        cleanup_old_deck_build_tasks()

        stale_in_progress.refresh_from_db()
        stale_building.refresh_from_db()
        recent_in_progress.refresh_from_db()
        stale_completed.refresh_from_db()

        self.assertEqual(stale_in_progress.status, DeckBuildStatus.FAILED)
        self.assertEqual(stale_building.status, DeckBuildStatus.FAILED)
        self.assertEqual(recent_in_progress.status, DeckBuildStatus.IN_PROGRESS)
        self.assertEqual(stale_completed.status, DeckBuildStatus.COMPLETED)

    @patch(f"{_MODULE}.datetime")
    def test_deletes_only_old_empty_invalid_decks(self, mock_datetime):
        """
        GIVEN decks with mixed validity, age, and card presence
        WHEN cleanup_old_deck_build_tasks runs
        THEN only invalid decks older than 1 day with no cards are deleted
        """
        mock_datetime.now.return_value = _FIXED_NOW

        user = self._create_user("decks")
        card = self._create_card("Cleanup Card")

        delete_me = Deck.objects.create(name="Delete Me", user=user, valid=False)
        keep_recent = Deck.objects.create(name="Keep Recent", user=user, valid=False)
        keep_valid = Deck.objects.create(name="Keep Valid", user=user, valid=True)
        keep_with_card = Deck.objects.create(name="Keep With Card", user=user, valid=False)
        DeckCard.objects.create(deck=keep_with_card, card=card, quantity=1)

        old_timestamp = _FIXED_NOW - timedelta(days=2)
        recent_timestamp = _FIXED_NOW - timedelta(hours=6)

        Deck.objects.filter(id=delete_me.id).update(created_at=old_timestamp)
        Deck.objects.filter(id=keep_recent.id).update(created_at=recent_timestamp)
        Deck.objects.filter(id=keep_valid.id).update(created_at=old_timestamp, valid=True)
        Deck.objects.filter(id=keep_with_card.id).update(created_at=old_timestamp)

        cleanup_old_deck_build_tasks()

        self.assertFalse(Deck.objects.filter(id=delete_me.id).exists())
        self.assertTrue(Deck.objects.filter(id=keep_recent.id).exists())
        self.assertTrue(Deck.objects.filter(id=keep_valid.id).exists())
        self.assertTrue(Deck.objects.filter(id=keep_with_card.id).exists())
