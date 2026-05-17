"""Chat LLM via OpenRouter (OpenAI-compatible /v1/chat/completions)."""

from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from app.config import get_settings


def _openrouter_headers() -> dict[str, str] | None:
    s = get_settings()
    headers: dict[str, str] = {}
    if s.openrouter_http_referer:
        headers["HTTP-Referer"] = s.openrouter_http_referer
    if s.openrouter_app_title:
        headers["X-Title"] = s.openrouter_app_title
    return headers or None


def get_chat_llm() -> BaseLanguageModel:
    s = get_settings()
    return ChatOpenAI(
        model=s.openrouter_chat_model,
        openai_api_key=s.openrouter_api_key,
        openai_api_base=s.openrouter_base_url,
        temperature=s.openrouter_temperature,
        default_headers=_openrouter_headers(),
    )
