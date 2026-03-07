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
