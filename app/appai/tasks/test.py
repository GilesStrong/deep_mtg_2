import os

import requests
from celery import Task, shared_task


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    soft_time_limit=90,
    time_limit=120,
)
def generate_text(self: Task, prompt: str, model: str = "gemma3:12b") -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
    r = requests.post(
        f"{base_url}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=(5, 110),
    )
    r.raise_for_status()
    return r.json()["response"]
