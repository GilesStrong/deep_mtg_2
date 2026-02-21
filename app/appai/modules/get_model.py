from app.app_settings import APP_SETTINGS
from beartype import beartype
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider


@beartype
def get_model(model_name: str) -> OpenAIChatModel | str:
    """
    Retrieve or configure a chat model based on the provided model name.

    This function determines whether to initialize an OpenAI-compatible chat model
    for Ollama or return the model name as-is for other providers.

    Args:
        model_name (str): The name/identifier of the model. If prefixed with "ollama:",
            an OpenAIChatModel instance will be created using Ollama provider settings.
            Otherwise, the model name is returned unchanged.

    Returns:
        OpenAIChatModel | str: Either an initialized OpenAIChatModel instance configured
            for Ollama (with custom settings for max_tokens and num_ctx), or the original
            model_name string for non-Ollama models.

    Example:
        >>> get_model("ollama:llama2")
        <OpenAIChatModel instance>
        >>> get_model("gpt-4")
        "gpt-4"
    """

    if model_name.startswith("ollama:"):
        model = OpenAIChatModel(
            model_name=model_name.split("ollama:")[1],
            provider=OllamaProvider(base_url=f"{APP_SETTINGS.OLLAMA_BASE_URL}/v1"),
            settings={
                'max_tokens': APP_SETTINGS.OLLAMA_MAX_TOKENS,
                'extra_body': {'options': {'num_ctx': APP_SETTINGS.OLLAMA_NUM_CTX}},
            },
        )
        return model
    else:
        return model_name
