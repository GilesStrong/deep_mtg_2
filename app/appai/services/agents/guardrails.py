import logfire
from aiocache import cached
from app.app_settings import APP_SETTINGS
from appuser.models.user import User
from asgiref.sync import sync_to_async
from beartype import beartype
from django.db.models import F
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from appai.constants.llm_models import TOOL_MODEL

GUARDRAIL_SYSTEM_PROMPT = """
# Overview
You are a guardrail agent that ensures the safety and integrity of LLM/AI usage.
Your primary role is to review user requests and determine whether they are relevant to the context of Magic: The Gathering.

# Input
You will receive the user's request in natural language.

# Output
You will output a Float value between 0.0 and 1.0, in which:
- 1.0 indicates that the user's request is highly relevant to Magic: The Gathering, and is safe to proceed with.
- 0.0 indicates that the user's request is not sufficiently relevant to Magic: The Gathering.
Based on this value, we will determine whether to allow the user's request to proceed or to block it.

# Considerations
When determining the relevance of the user's request, consider the following:
- Even if the user's request does not explicitly mention Magic: The Gathering, it may still be relevant if it pertains to topics commonly associated with Magic: The Gathering, such as card games, strategy games, fantasy themes, etc.
- If the user's request is ambiguous, and could potentially be relevant to Magic: The Gathering, it is safer to assume that it is relevant rather than not relevant, in order to avoid unnecessarily blocking legitimate requests.
- If the user's request is clearly about a topic that has no relation to Magic: The Gathering, such as asking about the weather, requesting a joke, or asking for general information about a non-Magic topic, then it is safe to assume that it is not relevant.
- If the user's request contains content that is inappropriate, harmful, or violates commonly accepted ethical guidelines, it should be considered not relevant, even if it has some tangential relation to Magic: The Gathering.
"""


class RelevancyScore(BaseModel):
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="A value between 0.0 and 1.0 indicating the relevance of the user's request to Magic: The Gathering.",
    )


@cached(ttl=3600)  # Cache for 1 hour
@beartype
async def guardrail_agent(user_request: str) -> RelevancyScore:
    """
    Guardrail agent that evaluates the relevance of a user's request to Magic: The Gathering.

    Args:
        user_request (str): The user's request in natural language.

    Returns:
        RelevancyScore: A value between 0.0 and 1.0 indicating the relevance of the user's request to Magic: The Gathering.
    """

    agent = Agent(
        model=TOOL_MODEL,
        system_prompt=GUARDRAIL_SYSTEM_PROMPT,
        output_retries=5,
        output_type=RelevancyScore,
    )

    response = await agent.run(user_request)

    return response.output


@beartype
async def is_request_relevant(user_request: str, user: User) -> bool:
    """
    Determines whether a user's request is relevant to Magic: The Gathering using the guardrail agent.

    Args:
        user_request (str): The user's request in natural language.
        user (User): The user making the request.

    Returns:
        bool: True if the user's request is relevant to Magic: The Gathering, False otherwise.

    Side-Effects:
        If the user's request is deemed too irrelevant, the user will be struck with a warning.
    """

    if user.warning_count >= APP_SETTINGS.N_WARNINGS_BEFORE_BLOCK:
        return False

    score = await guardrail_agent(user_request)
    if score.score < APP_SETTINGS.WARNING_THRESHOLD:
        user.warning_count = F("warning_count") + 1
        await sync_to_async(user.save)()
        user.refresh_from_db()
        return False

    elif score.score < APP_SETTINGS.BLOCKING_THRESHOLD:
        return False

    elif score.score >= APP_SETTINGS.WARNING_THRESHOLD and score.score >= APP_SETTINGS.BLOCKING_THRESHOLD:
        return True

    message = f"Something went wrong with the guardrail agent. Received an invalid score of {score.score} for user request: {user_request}"
    logfire.error(message)
    raise RuntimeError(message)
