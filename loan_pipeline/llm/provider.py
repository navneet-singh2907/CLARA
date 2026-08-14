"""Provider-neutral LangChain chat model construction and response handling."""

from typing import Any

from pydantic import SecretStr

from loan_pipeline.config import Settings

BEDROCK_PROVIDERS = frozenset({"bedrock", "aws-bedrock"})
OPENAI_COMPATIBLE_PROVIDERS = frozenset({"openai", "nebius"})


def is_bedrock_provider(settings: Settings) -> bool:
    return settings.llm_provider.strip().lower() in BEDROCK_PROVIDERS


def is_llm_configured(settings: Settings) -> bool:
    """Return whether the selected provider has its required configuration."""
    if is_bedrock_provider(settings):
        return bool(settings.bedrock_model_id and settings.aws_region)
    return bool(settings.llm_api_key)


def selected_model(settings: Settings, model: str | None = None) -> str:
    if model:
        return model
    if is_bedrock_provider(settings):
        return settings.bedrock_model_id
    return settings.openai_model


def build_chat_model(
    settings: Settings,
    *,
    model: str | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
) -> Any:
    """Build the configured LangChain chat client without storing AWS keys."""
    provider = settings.llm_provider.strip().lower()
    model_name = selected_model(settings, model)
    model_temperature = settings.llm_temperature if temperature is None else temperature

    if provider in BEDROCK_PROVIDERS:
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model=model_name,
            region_name=settings.aws_region,
            temperature=model_temperature,
        )

    if provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}.")
    if not settings.llm_api_key:
        raise RuntimeError(
            "The configured OpenAI-compatible provider requires LLM_API_KEY, "
            "NEBIUS_API_KEY, or OPENAI_API_KEY."
        )

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "api_key": SecretStr(settings.llm_api_key),
        "base_url": settings.llm_base_url,
        "model": model_name,
        "temperature": model_temperature,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    return ChatOpenAI(**kwargs)


def response_text(response: Any) -> str:
    """Normalize string and Bedrock content-block responses into plain text."""
    content = response.content if hasattr(response, "content") else response
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text = content.get("text")
        return text if isinstance(text, str) else str(content)
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
            elif isinstance(getattr(block, "text", None), str):
                text_parts.append(block.text)
        if text_parts:
            return "".join(text_parts)
    return str(content)
