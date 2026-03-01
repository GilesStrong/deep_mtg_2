from typing import Any

from app.app_settings import APP_SETTINGS
from appcore.modules.beartype import beartype
from celery import Task, shared_task

from appcards.modules.card_info import CardInfo
from appcards.modules.summarise_card import _summarise_card

queue_name = "llm" if "ollama:" in APP_SETTINGS.TEXT_MODEL else "default"
routing_key = queue_name


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    soft_time_limit=90,
    time_limit=120,
    queue=queue_name,
    routing_key=routing_key,
)
@beartype
def summarise_card(self: Task, card_details: dict[str, Any]) -> dict[str, str | list[str]]:
    return _summarise_card(CardInfo.model_validate(card_details)).model_dump()
