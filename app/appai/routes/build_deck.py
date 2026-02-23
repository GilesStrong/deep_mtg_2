from typing import Any, cast

import logfire
from appcards.models.deck import Deck
from celery.result import AsyncResult
from django.http import HttpRequest
from ninja import Path, Router
from ninja.errors import HttpError

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appai.serializers.build_deck import BuildDeckPostIn, BuildDeckPostOut, BuildDeckStatusIn, BuildDeckStatusOut
from appai.tasks.construct_deck import construct_deck

router = Router(tags=['decks'])


@router.post(
    '/',
    summary='Build a deck',
    description='Build a deck based on the provided prompt.',
    response={201: BuildDeckPostOut},
    operation_id='build_deck',
)
def build_deck(request: HttpRequest, payload: BuildDeckPostIn) -> BuildDeckPostOut:
    """
    mICDP3yor-ZYtmxJC2m_z

    Build a deck based on the provided prompt.
    The prompt should include the desired theme, strategy, or specific cards you want in the deck. Optionally, you can also provide a list of set codes to restrict the card selection to specific sets.

    The task will be processed asynchronously, and you will receive a task ID that can be used to check the status of the deck building process.
    """

    if payload.deck_id is not None:
        deck_id = payload.deck_id
    else:
        deck = Deck.objects.create(name="New Deck", user_id=payload.user_id)
        deck_id = deck.id

    # Enqueue the task to build the deck
    build = DeckBuildTask.objects.create(deck_id=deck_id, status=DeckBuildStatus.PENDING)

    task: AsyncResult = cast(Any, construct_deck.apply_async)(
        kwargs={
            "deck_description": payload.prompt,
            "deck_id": str(deck_id),
            "available_set_codes": payload.set_codes,
        },
        task_id=str(build.id),
    )

    if task.id != str(build.id):
        logfire.error(f"Task ID mismatch: expected {build.id}, got {task.id}")
        raise RuntimeError("Failed to enqueue deck building task")

    return BuildDeckPostOut(
        task_id=build.id,
        status_url=f'/api/app/ai/deck/build_status/{build.id}/',
        deck_id=deck_id,
    )


@router.get(
    '/build_status/{task_id}/',
    summary='Check deck build status',
    description='Check the status of a deck building task using the task ID.',
    response={200: BuildDeckStatusOut},
    operation_id='check_deck_build_status',
)
def check_deck_build_status(request: HttpRequest, path_params: Path[BuildDeckStatusIn]) -> BuildDeckStatusOut:
    """
    Check the status of a deck building task using the task ID.

    You can use the task ID received when you initiated the deck building process to check if the task is still processing, has completed successfully, or has failed. The response will include the current status of the task and the associated deck ID.
    """

    try:
        build = DeckBuildTask.objects.get(id=path_params.task_id)
    except DeckBuildTask.DoesNotExist:
        raise HttpError(404, 'Deck build task not found')

    return BuildDeckStatusOut(status=build.status, deck_id=build.deck_id)
