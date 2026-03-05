from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase
from ninja.errors import HttpError

from appai.models.deck_build import DeckBuildStatus
from appai.models.deck_build import DeckBuildTask as DeckBuildTaskModel
from appai.routes.build_deck import build_deck, check_deck_build_status, check_quota, get_deck_build_statuses

_MODULE = "appai.routes.build_deck"
_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TASK_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _quota_response(allowed: bool, remaining: int = 0):
    return SimpleNamespace(allowed=allowed, remaining=remaining)


class CheckQuotaRouteTests(TestCase):
    """Tests for check_quota endpoint."""

    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_returns_remaining_quota(self, mock_get_user, mock_get_redis, mock_check_quota):
        """
        GIVEN an authenticated user with a computed remaining quota
        WHEN check_quota is called
        THEN it returns a response containing that remaining quota value
        """
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=4)

        response = check_quota(MagicMock())

        self.assertEqual(response.remaining, 4)
        mock_check_quota.assert_called_once_with(mock_get_redis.return_value, _USER_ID)


class BuildStatusesRouteTests(TestCase):
    """Tests for get_deck_build_statuses endpoint."""

    def test_returns_all_statuses_and_pollable_subset(self):
        """
        GIVEN the deck build statuses endpoint
        WHEN get_deck_build_statuses is called
        THEN it returns all status values and the expected in-progress pollable subset
        """
        response = get_deck_build_statuses(MagicMock())

        self.assertIn(DeckBuildStatus.PENDING, response.all)
        self.assertIn(DeckBuildStatus.COMPLETED, response.all)
        self.assertIn(DeckBuildStatus.FAILED, response.all)
        self.assertEqual(
            response.pollable,
            [
                DeckBuildStatus.PENDING,
                DeckBuildStatus.IN_PROGRESS,
                DeckBuildStatus.BUILDING_DECK,
                DeckBuildStatus.CLASSIFYING_DECK_CARDS,
                DeckBuildStatus.FINDING_REPLACEMENT_CARDS,
            ],
        )


class BuildDeckRouteTests(TestCase):
    """Tests for build_deck endpoint."""

    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_blocks_when_daily_quota_already_exhausted(self, mock_get_user, mock_get_redis, mock_check_quota):
        """
        GIVEN a user with no allowed deck builds remaining before processing
        WHEN build_deck is called
        THEN it raises HttpError 429 and stops before enqueueing any task
        """
        payload = SimpleNamespace(prompt="build me a deck", set_codes=None, deck_id=None)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=False, remaining=0)

        with self.assertRaises(HttpError) as ctx:
            build_deck(MagicMock(), payload)

        self.assertEqual(ctx.exception.status_code, 429)

    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.DeckBuildTask")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_rejects_unowned_deck_id(
        self, mock_get_user, mock_get_redis, mock_check_quota, _mock_build_task, mock_deck
    ):
        """
        GIVEN a payload with deck_id that does not belong to the authenticated user
        WHEN build_deck is called
        THEN it raises HttpError 403
        """
        payload = SimpleNamespace(prompt="build me a deck", set_codes=None, deck_id=_DECK_ID)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=1)
        mock_deck.objects.filter.return_value.exists.return_value = False

        with self.assertRaises(HttpError) as ctx:
            build_deck(MagicMock(), payload)

        self.assertEqual(ctx.exception.status_code, 403)

    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.DeckBuildTask")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_blocks_regeneration_when_latest_build_is_pollable(
        self, mock_get_user, mock_get_redis, mock_check_quota, mock_build_task, mock_deck
    ):
        """
        GIVEN a provided deck_id whose latest build is in a pollable in-progress state
        WHEN build_deck is called for regeneration
        THEN it raises HttpError 409 and does not enqueue a new build
        """
        payload = SimpleNamespace(prompt="refine this deck", set_codes=None, deck_id=_DECK_ID)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=1)
        mock_deck.objects.filter.return_value.exists.return_value = True
        mock_build_task.objects.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(
            status=DeckBuildStatus.BUILDING_DECK
        )

        with self.assertRaises(HttpError) as ctx:
            build_deck(MagicMock(), payload)

        self.assertEqual(ctx.exception.status_code, 409)

    @patch(f"{_MODULE}.withdraw_from_daily_quota")
    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_blocks_when_quota_withdraw_fails(
        self, mock_get_user, mock_get_redis, mock_check_quota, mock_deck, mock_withdraw
    ):
        """
        GIVEN a user allowed at pre-check but denied during atomic quota withdrawal
        WHEN build_deck is called
        THEN it raises HttpError 429
        """
        payload = SimpleNamespace(prompt="build me a deck", set_codes=None, deck_id=_DECK_ID)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=1)
        mock_deck.objects.filter.return_value.exists.return_value = True
        mock_withdraw.return_value = _quota_response(allowed=False, remaining=0)

        with self.assertRaises(HttpError) as ctx:
            build_deck(MagicMock(), payload)

        self.assertEqual(ctx.exception.status_code, 429)

    @patch(f"{_MODULE}.is_request_relevant")
    @patch(f"{_MODULE}.withdraw_from_daily_quota")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_blocks_irrelevant_prompt(
        self, mock_get_user, mock_get_redis, mock_check_quota, mock_withdraw, mock_relevant
    ):
        """
        GIVEN a user with quota available but a prompt judged irrelevant by guardrails
        WHEN build_deck is called
        THEN it raises HttpError 400
        """
        payload = SimpleNamespace(prompt="tell me a joke", set_codes=None, deck_id=None)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=3)
        mock_withdraw.return_value = _quota_response(allowed=True, remaining=2)
        mock_relevant.return_value = False

        with self.assertRaises(HttpError) as ctx:
            build_deck(MagicMock(), payload)

        self.assertEqual(ctx.exception.status_code, 400)

    @patch(f"{_MODULE}.BuildDeckPostOut", side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    @patch(f"{_MODULE}.logfire.info")
    @patch(f"{_MODULE}.construct_deck")
    @patch(f"{_MODULE}.DeckBuildTask")
    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.is_request_relevant")
    @patch(f"{_MODULE}.withdraw_from_daily_quota")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_creates_new_deck_and_enqueues_task(
        self,
        mock_get_user,
        mock_get_redis,
        mock_check_quota,
        mock_withdraw,
        mock_relevant,
        mock_deck,
        mock_build_task,
        mock_construct_deck,
        _mock_logfire_info,
        _,
    ):
        """
        GIVEN a valid relevant prompt with available quota and no deck_id
        WHEN build_deck is called
        THEN it creates a deck, creates a task record, enqueues the worker task, and returns identifiers
        """
        payload = SimpleNamespace(prompt="mono-red aggro", set_codes=["FDN"], deck_id=None)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=3)
        mock_withdraw.return_value = _quota_response(allowed=True, remaining=2)
        mock_relevant.return_value = True

        deck = SimpleNamespace(id=_DECK_ID)
        build = SimpleNamespace(id=_TASK_ID)
        mock_deck.objects.create.return_value = deck
        mock_build_task.objects.create.return_value = build
        mock_construct_deck.apply_async.return_value = SimpleNamespace(id=str(_TASK_ID))

        result = build_deck(MagicMock(), payload)

        self.assertEqual(result.task_id, _TASK_ID)
        self.assertEqual(result.deck_id, _DECK_ID)
        self.assertEqual(result.status_url, f"/api/app/ai/deck/build_status/{_TASK_ID}/")
        mock_construct_deck.apply_async.assert_called_once()

    @patch(f"{_MODULE}.BuildDeckPostOut", side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    @patch(f"{_MODULE}.logfire.info")
    @patch(f"{_MODULE}.logfire.error")
    @patch(f"{_MODULE}.construct_deck")
    @patch(f"{_MODULE}.DeckBuildTask")
    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.is_request_relevant")
    @patch(f"{_MODULE}.withdraw_from_daily_quota")
    @patch(f"{_MODULE}.check_remaining_daily_quota")
    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.get_user_from_request")
    def test_raises_runtime_error_on_task_id_mismatch(
        self,
        mock_get_user,
        mock_get_redis,
        mock_check_quota,
        mock_withdraw,
        mock_relevant,
        mock_deck,
        mock_build_task,
        mock_construct_deck,
        _mock_logfire_error,
        _mock_logfire_info,
        _,
    ):
        """
        GIVEN the Celery async result ID differs from the created DeckBuildTask ID
        WHEN build_deck is called
        THEN it raises RuntimeError to prevent returning inconsistent task tracking data
        """
        payload = SimpleNamespace(prompt="mono-red aggro", set_codes=None, deck_id=None)
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_check_quota.return_value = _quota_response(allowed=True, remaining=3)
        mock_withdraw.return_value = _quota_response(allowed=True, remaining=2)
        mock_relevant.return_value = True

        mock_deck.objects.create.return_value = SimpleNamespace(id=_DECK_ID)
        mock_build_task.objects.create.return_value = SimpleNamespace(id=_TASK_ID)
        mock_construct_deck.apply_async.return_value = SimpleNamespace(id="cccccccc-cccc-cccc-cccc-cccccccccccc")

        with self.assertRaises(RuntimeError):
            build_deck(MagicMock(), payload)


class BuildDeckStatusRouteTests(TestCase):
    """Tests for check_deck_build_status endpoint."""

    @patch(f"{_MODULE}.DeckBuildTask")
    def test_returns_404_when_task_not_found(self, mock_build_task):
        """
        GIVEN a task_id that does not exist
        WHEN check_deck_build_status is called
        THEN it raises HttpError 404
        """
        mock_build_task.DoesNotExist = DeckBuildTaskModel.DoesNotExist
        mock_build_task.objects.get.side_effect = DeckBuildTaskModel.DoesNotExist

        with self.assertRaises(HttpError) as ctx:
            check_deck_build_status(MagicMock(), SimpleNamespace(task_id=_TASK_ID))

        self.assertEqual(ctx.exception.status_code, 404)

    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.get_user_from_request")
    @patch(f"{_MODULE}.DeckBuildTask")
    def test_returns_403_when_user_does_not_own_deck(self, mock_build_task, mock_get_user, mock_deck):
        """
        GIVEN an existing build task whose deck is not owned by the authenticated user
        WHEN check_deck_build_status is called
        THEN it raises HttpError 403
        """
        mock_build_task.DoesNotExist = DeckBuildTaskModel.DoesNotExist
        mock_build_task.objects.get.return_value = SimpleNamespace(
            id=_TASK_ID, deck=SimpleNamespace(id=_DECK_ID), status=DeckBuildStatus.PENDING
        )
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_deck.objects.filter.return_value.exists.return_value = False

        with self.assertRaises(HttpError) as ctx:
            check_deck_build_status(MagicMock(), SimpleNamespace(task_id=_TASK_ID))

        self.assertEqual(ctx.exception.status_code, 403)

    @patch(f"{_MODULE}.BuildDeckStatusOut", side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    @patch(f"{_MODULE}.Deck")
    @patch(f"{_MODULE}.get_user_from_request")
    @patch(f"{_MODULE}.DeckBuildTask")
    def test_returns_status_for_owned_deck(self, mock_build_task, mock_get_user, mock_deck, _):
        """
        GIVEN an existing build task for a deck owned by the authenticated user
        WHEN check_deck_build_status is called
        THEN it returns the task status and deck_id
        """
        build = SimpleNamespace(id=_TASK_ID, deck=SimpleNamespace(id=_DECK_ID), status=DeckBuildStatus.COMPLETED)
        mock_build_task.DoesNotExist = DeckBuildTaskModel.DoesNotExist
        mock_build_task.objects.get.return_value = build
        mock_get_user.return_value = SimpleNamespace(id=_USER_ID)
        mock_deck.objects.filter.return_value.exists.return_value = True

        response = check_deck_build_status(MagicMock(), SimpleNamespace(task_id=_TASK_ID))

        self.assertEqual(response.status, DeckBuildStatus.COMPLETED)
        self.assertEqual(response.deck_id, _DECK_ID)
