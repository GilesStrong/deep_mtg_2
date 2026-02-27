from __future__ import annotations

from django.conf import settings
from django.test import TestCase


class RuntimeTypecheckSettingsTests(TestCase):
    """Tests for runtime type-check settings during test execution."""

    def test_runtime_typechecks_are_disabled_in_tests(self):
        """
        GIVEN the Django test runner execution context
        WHEN runtime type-check settings are inspected
        THEN DISABLE_RUNTIME_TYPECHECKS is enabled to allow flexible mocking in unit tests
        """
        self.assertTrue(settings.DISABLE_RUNTIME_TYPECHECKS)
