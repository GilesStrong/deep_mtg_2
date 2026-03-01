from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import redis
from django.test import TestCase

from appauth.modules.auth_rate_limit import _extract_client_ip, check_auth_rate_limit

_MODULE = "appauth.modules.auth_rate_limit"


class ExtractClientIpTests(TestCase):
    def test_prefers_first_x_forwarded_for_hop(self):
        """
        GIVEN a request with an X-Forwarded-For header containing multiple IPs
        WHEN _extract_client_ip is called
        THEN it returns the first (leftmost) IP in the header
        """
        request = SimpleNamespace(
            headers={"X-Forwarded-For": "203.0.113.8, 10.0.0.2"}, META={"REMOTE_ADDR": "10.0.0.3"}
        )

        self.assertEqual(_extract_client_ip(request), "203.0.113.8")

    def test_falls_back_to_remote_addr(self):
        """
        GIVEN a request with no X-Forwarded-For header but a REMOTE_ADDR in META
        WHEN _extract_client_ip is called
        THEN it returns the REMOTE_ADDR value
        """
        request = SimpleNamespace(headers={}, META={"REMOTE_ADDR": "10.0.0.3"})

        self.assertEqual(_extract_client_ip(request), "10.0.0.3")

    def test_returns_unknown_when_no_ip_data(self):
        """
        GIVEN a request with no X-Forwarded-For header and no REMOTE_ADDR in META
        WHEN _extract_client_ip is called
        THEN it returns the string 'unknown'
        """
        request = SimpleNamespace(headers={}, META={})

        self.assertEqual(_extract_client_ip(request), "unknown")


class CheckAuthRateLimitTests(TestCase):
    def test_disallows_when_limit_non_positive(self):
        """
        GIVEN a rate limit configured with a non-positive limit value
        WHEN check_auth_rate_limit is called
        THEN it immediately disallows the request and returns the window as retry_after_seconds
        """
        request = SimpleNamespace(headers={}, META={"REMOTE_ADDR": "10.0.0.3"})

        result = check_auth_rate_limit(request, action="exchange", limit=0, window_seconds=60)

        self.assertFalse(result.allowed)
        self.assertEqual(result.retry_after_seconds, 60)

    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.time.time")
    def test_allows_under_limit_and_sets_expiry(self, mock_time, mock_get_redis):
        """
        GIVEN a Redis counter that is below the configured limit and a positive TTL
        WHEN check_auth_rate_limit is called
        THEN it allows the request, sets an expiry on the key, and returns the TTL as retry_after_seconds
        """
        mock_time.return_value = 1700000000
        redis_client = mock_get_redis.return_value
        redis_client.incr.return_value = 1
        redis_client.ttl.return_value = 55

        request = SimpleNamespace(headers={"X-Forwarded-For": "203.0.113.8"}, META={})
        result = check_auth_rate_limit(request, action="refresh", limit=3, window_seconds=60)

        self.assertTrue(result.allowed)
        self.assertEqual(result.retry_after_seconds, 55)
        redis_client.expire.assert_called_once()

    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.time.time")
    def test_blocks_over_limit(self, mock_time, mock_get_redis):
        """
        GIVEN a Redis counter that exceeds the configured limit
        WHEN check_auth_rate_limit is called
        THEN it disallows the request and returns the remaining TTL as retry_after_seconds
        """
        mock_time.return_value = 1700000000
        redis_client = mock_get_redis.return_value
        redis_client.incr.return_value = 4
        redis_client.ttl.return_value = 42

        request = SimpleNamespace(headers={}, META={"REMOTE_ADDR": "10.0.0.3"})
        result = check_auth_rate_limit(request, action="exchange", limit=3, window_seconds=60)

        self.assertFalse(result.allowed)
        self.assertEqual(result.retry_after_seconds, 42)

    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.time.time")
    def test_uses_window_when_ttl_missing(self, mock_time, mock_get_redis):
        """
        GIVEN a Redis counter below the limit but a TTL of -1 (key has no expiry)
        WHEN check_auth_rate_limit is called
        THEN it allows the request and falls back to the full window_seconds as retry_after_seconds
        """
        mock_time.return_value = 1700000000
        redis_client = mock_get_redis.return_value
        redis_client.incr.return_value = 2
        redis_client.ttl.return_value = -1

        request = SimpleNamespace(headers={}, META={"REMOTE_ADDR": "10.0.0.3"})
        result = check_auth_rate_limit(request, action="refresh", limit=5, window_seconds=60)

        self.assertTrue(result.allowed)
        self.assertEqual(result.retry_after_seconds, 60)

    @patch(f"{_MODULE}.get_redis")
    @patch(f"{_MODULE}.time.time")
    def test_fails_open_on_redis_error(self, mock_time, mock_get_redis):
        """
        GIVEN Redis raises a RedisError during the incr call
        WHEN check_auth_rate_limit is called
        THEN it fails open by allowing the request and returns retry_after_seconds of 0
        """
        mock_time.return_value = 1700000000
        redis_client = mock_get_redis.return_value
        redis_client.incr.side_effect = redis.RedisError("redis unavailable")

        request = SimpleNamespace(headers={}, META={"REMOTE_ADDR": "10.0.0.3"})
        result = check_auth_rate_limit(request, action="exchange", limit=3, window_seconds=60)

        self.assertTrue(result.allowed)
        self.assertEqual(result.retry_after_seconds, 0)
