from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID
from zoneinfo import ZoneInfo

from django.test import TestCase

from appai.modules.build_rate_limit import (
    _seconds_until_local_midnight,
    check_remaining_daily_quota,
    withdraw_from_daily_quota,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_TIMEZONE = ZoneInfo("America/New_York")
_USER_ID = UUID("12345678-1234-5678-1234-567812345678")

# Freeze a known "now" so tests are deterministic
_NOW = datetime(2024, 6, 15, 14, 30, 0, tzinfo=_TEST_TIMEZONE)


def _make_redis(get_value=None, incr_value=1, ttl_value=3600):
    """Return a MagicMock that mimics the subset of redis.Redis used here."""
    r = MagicMock()
    r.get.return_value = get_value
    r.incr.return_value = incr_value
    r.ttl.return_value = ttl_value
    r.expire.return_value = True
    return r


# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_MODULE = "appai.modules.build_rate_limit"


class SecondsUntilLocalMidnightTests(TestCase):
    """Tests for _seconds_until_local_midnight."""

    def _call(self, now: datetime) -> int:
        return _seconds_until_local_midnight(now)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    def test_returns_positive_integer(self):
        """
        GIVEN a timezone-aware datetime in the middle of the day
        WHEN _seconds_until_local_midnight is called
        THEN it returns a positive integer
        """
        result = self._call(_NOW)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    def test_mid_day_roughly_correct(self):
        """
        GIVEN a datetime of 14:30 local time
        WHEN _seconds_until_local_midnight is called
        THEN the result is approximately 34200 seconds (9.5 hours) within a 60-second tolerance
        """
        result = self._call(_NOW)
        self.assertAlmostEqual(result, 34200, delta=60)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    def test_one_second_before_midnight_returns_at_least_one(self):
        """
        GIVEN a datetime of 23:59:59 local time (one second before midnight)
        WHEN _seconds_until_local_midnight is called
        THEN it returns at least 1 to avoid zero or negative TTLs
        """
        nearly_midnight = datetime(2024, 6, 15, 23, 59, 59, tzinfo=_TEST_TIMEZONE)
        result = self._call(nearly_midnight)
        self.assertGreaterEqual(result, 1)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    def test_exactly_midnight_returns_at_least_one(self):
        """
        GIVEN a datetime of exactly 00:00:00 local time (the start of a new day)
        WHEN _seconds_until_local_midnight is called
        THEN it returns at least 1, targeting the following midnight
        """
        midnight = datetime(2024, 6, 16, 0, 0, 0, tzinfo=_TEST_TIMEZONE)
        result = self._call(midnight)
        self.assertGreaterEqual(result, 1)


class CheckRemainingDailyQuotaTests(TestCase):
    """Tests for check_remaining_daily_quota."""

    def _call(self, redis_client, user_id=_USER_ID):
        return check_remaining_daily_quota(redis_client, user_id)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_no_key_full_quota(self, mock_settings, mock_dt):
        """
        GIVEN a user with no Redis key (no builds today) and a daily limit of 5
        WHEN check_remaining_daily_quota is called
        THEN the result is allowed with 5 remaining and no retry delay
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=None)

        result = self._call(r)

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 5)
        self.assertEqual(result.limit, 5)
        self.assertEqual(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_partial_usage(self, mock_settings, mock_dt):
        """
        GIVEN a user who has already performed 3 out of 5 allowed builds today
        WHEN check_remaining_daily_quota is called
        THEN the result is allowed with 2 remaining and no retry delay
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=b"3")

        result = self._call(r)

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 2)
        self.assertEqual(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_at_limit_blocked(self, mock_settings, mock_dt):
        """
        GIVEN a user who has already used all 5 allowed builds today
        WHEN check_remaining_daily_quota is called
        THEN the result is not allowed, remaining is 0, and retry_after_seconds is positive
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=b"5")

        result = self._call(r)

        self.assertFalse(result.allowed)
        self.assertEqual(result.remaining, 0)
        self.assertGreater(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_over_limit_blocked(self, mock_settings, mock_dt):
        """
        GIVEN a user whose Redis count (99) exceeds the daily limit of 5
        WHEN check_remaining_daily_quota is called
        THEN the result is not allowed and remaining is clamped to 0
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=b"99")

        result = self._call(r)

        self.assertFalse(result.allowed)
        self.assertEqual(result.remaining, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_corrupt_redis_value_treated_as_zero(self, mock_settings, mock_dt):
        """
        GIVEN a Redis key that contains a non-numeric value (corrupted data)
        WHEN check_remaining_daily_quota is called
        THEN the count is treated as 0, granting full quota as a safe fallback
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=b"not-a-number")

        result = self._call(r)

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 5)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_redis_key_uses_correct_user_and_day(self, mock_settings, mock_dt):
        """
        GIVEN a specific user ID and a frozen date of 2024-06-15
        WHEN check_remaining_daily_quota is called
        THEN Redis is queried with the key in the format quota:deckbuild:<user_id>:<YYYYMMDD>
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=None)

        self._call(r)

        expected_key = f"quota:deckbuild:{_USER_ID}:20240615"
        r.get.assert_called_once_with(expected_key)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_reset_at_is_future(self, mock_settings, mock_dt):
        """
        GIVEN a user with quota remaining and a frozen current time
        WHEN check_remaining_daily_quota is called
        THEN reset_at is a datetime strictly after the current time
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(get_value=None)

        result = self._call(r)

        self.assertGreater(result.reset_at, _NOW)


class WithdrawFromDailyQuotaTests(TestCase):
    """Tests for withdraw_from_daily_quota."""

    def _call(self, redis_client, user_id=_USER_ID):
        return withdraw_from_daily_quota(redis_client, user_id)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_first_call_sets_ttl(self, mock_settings, mock_dt):
        """
        GIVEN a user with no prior builds today (INCR returns 1)
        WHEN withdraw_from_daily_quota is called
        THEN Redis expire is called once to set the TTL on the new key
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=1, ttl_value=34200)

        self._call(r)

        r.expire.assert_called_once()
        args = r.expire.call_args[0]
        self.assertIn("quota:deckbuild:", args[0])

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_subsequent_call_with_valid_ttl_does_not_reset_expire(self, mock_settings, mock_dt):
        """
        GIVEN a user with an existing Redis key that still has a valid TTL (INCR returns 2)
        WHEN withdraw_from_daily_quota is called
        THEN Redis expire is not called again, preserving the original expiry
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=2, ttl_value=34200)

        self._call(r)

        r.expire.assert_not_called()

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_lost_ttl_is_restored(self, mock_settings, mock_dt):
        """
        GIVEN a user whose Redis key has lost its TTL (ttl returns -1, count is 2)
        WHEN withdraw_from_daily_quota is called
        THEN Redis expire is called to restore the TTL and prevent a permanently persisted key
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=2, ttl_value=-1)

        self._call(r)

        r.expire.assert_called_once()

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_within_limit_allowed(self, mock_settings, mock_dt):
        """
        GIVEN a user whose post-increment count (3) is below the daily limit of 5
        WHEN withdraw_from_daily_quota is called
        THEN the result is allowed with 2 remaining and no retry delay
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=3, ttl_value=34200)

        result = self._call(r)

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 2)
        self.assertEqual(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_exactly_at_limit_allowed(self, mock_settings, mock_dt):
        """
        GIVEN a user whose post-increment count equals the daily limit of 5 (last allowed build)
        WHEN withdraw_from_daily_quota is called
        THEN the result is allowed with 0 remaining and no retry delay
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=5, ttl_value=34200)

        result = self._call(r)

        self.assertTrue(result.allowed)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_over_limit_blocked(self, mock_settings, mock_dt):
        """
        GIVEN a user whose post-increment count (6) exceeds the daily limit of 5
        WHEN withdraw_from_daily_quota is called
        THEN the result is not allowed, remaining is 0, and retry_after_seconds is positive
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=6, ttl_value=34200)

        result = self._call(r)

        self.assertFalse(result.allowed)
        self.assertEqual(result.remaining, 0)
        self.assertGreater(result.retry_after_seconds, 0)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_correct_redis_key_format(self, mock_settings, mock_dt):
        """
        GIVEN a specific user ID and a frozen date of 2024-06-15
        WHEN withdraw_from_daily_quota is called
        THEN Redis INCR is called with the key in the format quota:deckbuild:<user_id>:<YYYYMMDD>
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=1, ttl_value=34200)

        self._call(r)

        expected_key = f"quota:deckbuild:{_USER_ID}:20240615"
        r.incr.assert_called_once_with(expected_key)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_result_limit_matches_settings(self, mock_settings, mock_dt):
        """
        GIVEN a daily limit of 10 configured in APP_SETTINGS
        WHEN withdraw_from_daily_quota is called
        THEN the returned LimitResult.limit field equals 10
        """
        mock_settings.DECK_BUILDS_PER_DAY = 10
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=1, ttl_value=34200)

        result = self._call(r)

        self.assertEqual(result.limit, 10)

    @patch(f"{_MODULE}.LOCAL_TIMEZONE", _TEST_TIMEZONE)
    @patch(f"{_MODULE}.datetime")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_reset_at_is_future(self, mock_settings, mock_dt):
        """
        GIVEN a user within their daily quota and a frozen current time
        WHEN withdraw_from_daily_quota is called
        THEN reset_at is a datetime strictly after the current time
        """
        mock_settings.DECK_BUILDS_PER_DAY = 5
        mock_settings.LOCALITY = "America/New_York"
        mock_dt.now.return_value = _NOW
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        r = _make_redis(incr_value=1, ttl_value=34200)

        result = self._call(r)

        self.assertGreater(result.reset_at, _NOW)
