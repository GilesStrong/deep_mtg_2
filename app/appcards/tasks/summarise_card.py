from typing import Any

from beartype import beartype
from celery import Task, shared_task

from appcards.modules.card_info import CardInfo
from appcards.modules.summarise_card import summarise_card as _summarise_card


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    soft_time_limit=90,
    time_limit=120,
    queue="llm",
    routing_key="llm",
)
@beartype
def summarise_card(self: Task, card_details: dict[str, Any]) -> str:
    return _summarise_card(self, CardInfo.model_validate(card_details))
