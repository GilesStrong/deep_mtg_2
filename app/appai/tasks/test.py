import requests
from celery import Task, shared_task
from pydantic_ai import Agent

from appai.modules.get_model import get_model


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    soft_time_limit=90,
    time_limit=120,
    queue="llm",
    routing_key="llm",
)
def generate_text(self: Task, prompt: str, model: str = "gemma3:12b") -> str:
    get_model_task = get_model(model_name=model)
    agent = Agent(model=get_model_task)
    return agent.run_sync(prompt).output
