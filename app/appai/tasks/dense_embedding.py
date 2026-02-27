from appcore.modules.beartype import beartype
from celery import Task, shared_task

from appai.modules.dense_embedding import _dense_embed


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
def dense_embed(self: Task, text: str) -> list[float]:
    return _dense_embed(text)
