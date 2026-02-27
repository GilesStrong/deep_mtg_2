from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

from appai.modules.dense_embedding import _dense_embed, dense_embed

_MODULE = "appai.modules.dense_embedding"

_SAMPLE_TEXT = "A red aggro deck with burn spells"
_SAMPLE_EMBEDDING = [0.1, 0.2, 0.3, 0.4]


class DenseEmbedInternalTests(TestCase):
    """Tests for the internal _dense_embed function."""

    def setUp(self):
        # Clear LRU cache between tests to avoid cross-test pollution
        _dense_embed.cache_clear()

    def tearDown(self):
        _dense_embed.cache_clear()

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_posts_to_correct_url(self, mock_post, mock_settings):
        """
        GIVEN an Ollama base URL configured in APP_SETTINGS
        WHEN _dense_embed is called
        THEN a POST request is made to <OLLAMA_BASE_URL>/api/embeddings
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        _dense_embed(_SAMPLE_TEXT)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://ollama:11434/api/embeddings")

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_sends_correct_model_and_prompt(self, mock_post, mock_settings):
        """
        GIVEN a configured embedding model and an input text
        WHEN _dense_embed is called
        THEN the POST body contains the correct model and prompt fields
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        _dense_embed(_SAMPLE_TEXT)

        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["json"]["model"], "nomic-embed-text")
        self.assertEqual(call_kwargs["json"]["prompt"], _SAMPLE_TEXT)

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_uses_60_second_timeout(self, mock_post, mock_settings):
        """
        GIVEN a request to the embeddings API
        WHEN _dense_embed is called
        THEN the request is made with a 60-second timeout
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        _dense_embed(_SAMPLE_TEXT)

        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 60)

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_returns_embedding_from_response(self, mock_post, mock_settings):
        """
        GIVEN the API returns a valid embedding list
        WHEN _dense_embed is called
        THEN the returned value is that embedding list
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        result = _dense_embed(_SAMPLE_TEXT)

        self.assertEqual(result, _SAMPLE_EMBEDDING)

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_raises_on_http_error(self, mock_post, mock_settings):
        """
        GIVEN the API returns an error status code
        WHEN _dense_embed is called
        THEN an HTTPError is raised
        """
        import requests as req

        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        with self.assertRaises(req.exceptions.HTTPError):
            _dense_embed(_SAMPLE_TEXT)

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_result_is_cached(self, mock_post, mock_settings):
        """
        GIVEN the same text is passed twice
        WHEN _dense_embed is called twice
        THEN the HTTP request is only made once due to LRU caching
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        _dense_embed(_SAMPLE_TEXT)
        _dense_embed(_SAMPLE_TEXT)

        self.assertEqual(mock_post.call_count, 1)


class DenseEmbedOutsideCeleryTests(TestCase):
    """Tests for dense_embed when called outside a Celery task."""

    def setUp(self):
        _dense_embed.cache_clear()

    def tearDown(self):
        _dense_embed.cache_clear()

    @patch(f"{_MODULE}.in_celery_task", return_value=False)
    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_calls_internal_embed_directly(self, mock_post, mock_settings, mock_in_celery):
        """
        GIVEN the function is called outside a Celery task
        WHEN dense_embed is called
        THEN it directly calls _dense_embed and returns the embedding
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        result = dense_embed(_SAMPLE_TEXT)

        self.assertEqual(result, _SAMPLE_EMBEDDING)
        mock_post.assert_called_once()

    @patch(f"{_MODULE}.in_celery_task", return_value=False)
    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.post")
    def test_does_not_delegate_to_celery_task(self, mock_post, mock_settings, mock_in_celery):
        """
        GIVEN the function is called outside a Celery task
        WHEN dense_embed is called
        THEN no Celery task is dispatched
        """
        mock_settings.OLLAMA_BASE_URL = "http://ollama:11434"
        mock_settings.EMBEDDING_MODEL = "nomic-embed-text"
        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": _SAMPLE_EMBEDDING}
        mock_post.return_value = mock_response

        with patch.dict("sys.modules", {"appai.tasks.dense_embedding": MagicMock()}):
            dense_embed(_SAMPLE_TEXT)

        # Confirm the real HTTP path was taken, not a mocked task
        mock_post.assert_called_once()


class DenseEmbedInsideCeleryTests(TestCase):
    """Tests for dense_embed when called inside a Celery task."""

    def setUp(self):
        _dense_embed.cache_clear()

    def tearDown(self):
        _dense_embed.cache_clear()

    @patch(f"{_MODULE}.in_celery_task", return_value=True)
    def test_delegates_to_celery_task(self, mock_in_celery):
        """
        GIVEN the function is called inside a Celery task
        WHEN dense_embed is called
        THEN it dispatches a Celery task and returns the task result
        """
        mock_task = MagicMock()
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = _SAMPLE_EMBEDDING
        mock_task.delay.return_value = mock_async_result

        with patch.dict("sys.modules", {"appai.tasks.dense_embedding": MagicMock(dense_embed=mock_task)}):
            result = dense_embed(_SAMPLE_TEXT)

        self.assertEqual(result, _SAMPLE_EMBEDDING)

    @patch(f"{_MODULE}.in_celery_task", return_value=True)
    def test_celery_task_called_with_correct_text(self, mock_in_celery):
        """
        GIVEN the function is called inside a Celery task with specific text
        WHEN dense_embed is called
        THEN the Celery task is dispatched with that same text
        """
        mock_task = MagicMock()
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = _SAMPLE_EMBEDDING
        mock_task.delay.return_value = mock_async_result

        with patch.dict("sys.modules", {"appai.tasks.dense_embedding": MagicMock(dense_embed=mock_task)}):
            dense_embed(_SAMPLE_TEXT)

        mock_task.delay.assert_called_once_with(_SAMPLE_TEXT)

    @patch(f"{_MODULE}.in_celery_task", return_value=True)
    def test_celery_result_get_called_with_60s_timeout(self, mock_in_celery):
        """
        GIVEN the function is called inside a Celery task
        WHEN dense_embed is called
        THEN result.get is called with a 60-second timeout
        """
        mock_task = MagicMock()
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = _SAMPLE_EMBEDDING
        mock_task.delay.return_value = mock_async_result

        with patch.dict("sys.modules", {"appai.tasks.dense_embedding": MagicMock(dense_embed=mock_task)}):
            dense_embed(_SAMPLE_TEXT)

        mock_async_result.get.assert_called_once_with(timeout=60)

    @patch(f"{_MODULE}.in_celery_task", return_value=True)
    @patch(f"{_MODULE}.requests.post")
    def test_does_not_call_http_directly_inside_celery(self, mock_post, mock_in_celery):
        """
        GIVEN the function is called inside a Celery task
        WHEN dense_embed is called
        THEN no direct HTTP request is made to the Ollama API
        """
        mock_task = MagicMock()
        mock_async_result = MagicMock()
        mock_async_result.get.return_value = _SAMPLE_EMBEDDING
        mock_task.delay.return_value = mock_async_result

        with patch.dict("sys.modules", {"appai.tasks.dense_embedding": MagicMock(dense_embed=mock_task)}):
            dense_embed(_SAMPLE_TEXT)

        mock_post.assert_not_called()
