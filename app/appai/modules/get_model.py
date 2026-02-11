from beartype import beartype
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from app.app_settings import APP_SETTINGS


@beartype
def get_model(model_name: str) -> OpenAIChatModel:
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url=f"{APP_SETTINGS.OLLAMA_BASE_URL}/v1"),
        settings={
            'max_tokens': APP_SETTINGS.OLLAMA_MAX_TOKENS,
            'extra_body': {'options': {'num_ctx': APP_SETTINGS.OLLAMA_NUM_CTX}},
        },
    )
    return model
