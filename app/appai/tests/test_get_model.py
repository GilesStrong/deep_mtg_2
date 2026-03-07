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

from unittest.mock import patch

from django.test import TestCase

from appai.modules.get_model import get_model

_MODULE = "appai.modules.get_model"


class GetModelTests(TestCase):
    """Tests for get_model."""

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.OpenAIChatModel")
    @patch(f"{_MODULE}.OllamaProvider")
    def test_ollama_model_returns_configured_chat_model(self, mock_provider, mock_openai_model, mock_settings):
        """
        GIVEN a model name prefixed with 'ollama:' and configured Ollama settings
        WHEN get_model is called
        THEN it returns an OpenAIChatModel configured with the stripped model name and Ollama provider
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.OLLAMA_MAX_TOKENS = 2048
        mock_settings.OLLAMA_NUM_CTX = 8192

        result = get_model("ollama:llama3.1")

        mock_provider.assert_called_once_with(base_url="http://ollama:11434/v1")
        mock_openai_model.assert_called_once_with(
            model_name="llama3.1",
            provider=mock_provider.return_value,
            settings={
                "max_tokens": 2048,
                "extra_body": {"options": {"num_ctx": 8192}},
            },
        )
        self.assertEqual(result, mock_openai_model.return_value)

    @patch(f"{_MODULE}.OpenAIChatModel")
    @patch(f"{_MODULE}.OllamaProvider")
    def test_non_ollama_model_returns_input_name(self, mock_provider, mock_openai_model):
        """
        GIVEN a model name without the 'ollama:' prefix
        WHEN get_model is called
        THEN it returns the model name unchanged and does not initialize Ollama/OpenAI wrappers
        """
        result = get_model("gpt-4.1-mini")

        self.assertEqual(result, "gpt-4.1-mini")
        mock_provider.assert_not_called()
        mock_openai_model.assert_not_called()
