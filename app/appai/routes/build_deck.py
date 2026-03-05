from typing import Any, cast

import logfire
from appauth.modules.auth import get_user_from_request
from appcards.models.deck import Deck
from appcore.modules.redis_client import get_redis
from celery.result import AsyncResult
from django.http import HttpRequest
from ninja import Path, Router
from ninja.errors import HttpError

from appai.constants.guardrail_contexts import BUILD_DECK_CONTEXT
from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appai.modules.build_rate_limit import check_remaining_daily_quota, withdraw_from_daily_quota
from appai.serializers.build_deck import (
    BuildDeckPostIn,
    BuildDeckPostOut,
    BuildDeckStatusIn,
    BuildDeckStatusOut,
    CheckQuotaOut,
)
from appai.services.agents.guardrails import is_request_relevant
from appai.tasks.construct_deck import construct_deck

router = Router(tags=['decks'])


@router.get(
    '/remaining_quota/',
    summary='Check remaining daily deck build quota',
    description='Check the remaining daily quota for building decks. This endpoint returns the number of decks you can still build today based on your daily limit.',
    response={200: CheckQuotaOut},
    operation_id='check_remaining_daily_quota',
)
def check_quota(request: HttpRequest) -> CheckQuotaOut:
    """
    Check the remaining daily quota for building decks.

    This endpoint allows you to check how many decks you can still build today based on your daily limit. The response will return the number of remaining deck builds you have for the current day. If you have exceeded your quota, it will return 0.

    Args:
        request (HttpRequest): The incoming HTTP request object, used to identify the user making the request.

    Returns:
        CheckQuotaOut: An object containing the number of remaining deck builds you can perform today.
    """
    user = get_user_from_request(request)
    response = check_remaining_daily_quota(get_redis(), user.id)
    return CheckQuotaOut(remaining=response.remaining)


@router.post(
    '/',
    summary='Build a deck',
    description='Build a deck based on the provided prompt.',
    response={201: BuildDeckPostOut},
    operation_id='build_deck',
)
def build_deck(request: HttpRequest, payload: BuildDeckPostIn) -> BuildDeckPostOut:
    """
    Build a deck based on the provided prompt.
    The prompt should include the desired theme, strategy, or specific cards you want in the deck. Optionally, you can also provide a list of set codes to restrict the card selection to specific sets.

    The task will be processed asynchronously, and you will receive a task ID that can be used to check the status of the deck building process.
    The deck will be created or updated based on the provided deck ID. If no deck ID is provided, a new deck will be created for the user.
    Building decks is subject to a daily quota, so please ensure you have remaining quota before initiating the process. You can check your remaining quota using the appropriate endpoint.

    Args:
        request (HttpRequest): The incoming HTTP request object, used to identify the user making the request.
        payload (BuildDeckPostIn): The input data containing the deck description and optional set codes.

    Returns:
        BuildDeckPostOut: An object containing the task ID, status URL, and deck ID associated with the deck building task.
    """

    # Check reminaing quota before proceeding
    user = get_user_from_request(request)
    redis_client = get_redis()
    response = check_remaining_daily_quota(redis_client, user.id)
    if not response.allowed:
        raise HttpError(429, "Daily deck build quota exceeded")

    # Check is user can update the deck if deck_id is provided
    if payload.deck_id is not None:
        deck_id = payload.deck_id
        if not Deck.objects.filter(id=deck_id, user_id=user.id).exists():
            raise HttpError(403, "You do not have permission to access this deck")

    # Withdraw from quota
    response = withdraw_from_daily_quota(redis_client, user.id)
    if not response.allowed:
        raise HttpError(429, "Daily deck build quota exceeded")

    # Check user can proceed with the request based on guardrails
    relevant = is_request_relevant(payload.prompt, context=BUILD_DECK_CONTEXT, user=user)
    if not relevant:
        raise HttpError(400, "Your request is not relevant to Magic: The Gathering and cannot be processed")

    # If deck_id is not provided, create a new deck for the user
    if payload.deck_id is None:
        logfire.info(f"Creating new deck for user {user.id} as no deck_id was provided")
        deck = Deck.objects.create(name="New Deck", user_id=user.id)
        deck_id = deck.id
    else:
        logfire.info(f"Using provided deck_id {payload.deck_id} for user {user.id}")
        deck_id = payload.deck_id

    # Enqueue the task to build the deck
    build = DeckBuildTask.objects.create(deck_id=deck_id, status=DeckBuildStatus.PENDING)

    task: AsyncResult = cast(Any, construct_deck.apply_async)(
        kwargs={
            "deck_description": payload.prompt,
            "deck_id": str(deck_id),
            "user_id": str(user.id),
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
        deck_id = build.deck.id
        user = get_user_from_request(request)
        if not Deck.objects.filter(id=deck_id, user_id=user.id).exists():
            raise HttpError(403, "You do not have permission to access this deck")
    except DeckBuildTask.DoesNotExist:
        raise HttpError(404, 'Deck build task not found')

    return BuildDeckStatusOut(status=build.status, deck_id=deck_id)
