import argparse
from typing import Any

from appai.tasks.test import generate_text
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Add multiple cards to the database'

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    def handle(self, *args: Any, **options: Any) -> None:
        from django.conf import settings

        print('BROKER', settings.CELERY_BROKER_URL)
        print('BACKEND', getattr(settings, 'CELERY_RESULT_BACKEND', None))
        r = generate_text.delay("Say hi in the style of a Magic card rules text.")
        # base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        # r = requests.post(
        #     f"{base_url}/api/generate",
        #     json={"model": "gpt-oss:20b", "prompt": "Say hi in the style of a Magic card rules text.", "stream": False},
        #     timeout=120,
        # )
        # r.raise_for_status()
        # print(r.json()["response"])
        print(r.id)
        print(r.get())
