from celery import current_task


def in_celery_task() -> bool:
    return bool(current_task and current_task.request and current_task.request.id)
