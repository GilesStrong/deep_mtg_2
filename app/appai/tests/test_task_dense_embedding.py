from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from appai.tasks.dense_embedding import dense_embed

_MODULE = "appai.tasks.dense_embedding"


class DenseEmbedTaskTests(TestCase):
    """Tests for the dense_embed Celery task wrapper."""

    @patch(f"{_MODULE}._dense_embed")
    def test_delegates_to_module_dense_embed(self, mock_dense_embed):
        """
        GIVEN text input passed to the Celery task wrapper
        WHEN dense_embed is called
        THEN it delegates to appai.modules.dense_embedding._dense_embed and returns that value
        """
        mock_dense_embed.return_value = [0.1, 0.2, 0.3]

        result = dense_embed("Lightning Bolt")

        self.assertEqual(result, [0.1, 0.2, 0.3])
        mock_dense_embed.assert_called_once_with("Lightning Bolt")
