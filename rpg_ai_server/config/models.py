from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .settings import settings


def create_gemini_model(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.models.gemini_model,
        temperature=temperature,
        google_api_key=settings.app.google_api_key,
    )


def create_openrouter_model(
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 8192,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.app.openrouter_api_key,
        base_url=settings.app.openrouter_base_url,
        default_headers={
            "HTTP-Referer": "https://rpg-ai-server.local",
            "X-Title": "RPG AI Server",
        },
    )


def get_image_model():
    return create_openrouter_model(settings.models.image_model, temperature=0.1, max_tokens=4096)


def get_redescription_model():
    return create_openrouter_model(settings.models.redescription_model, temperature=0.2, max_tokens=32768)


def get_tool_agent_model():
    return create_openrouter_model(settings.models.tool_agent_model, temperature=0.3, max_tokens=8192)


def get_context_injector_model():
    return create_openrouter_model(settings.models.context_injector_model, temperature=0.1, max_tokens=4096)


def get_story_model():
    return create_openrouter_model(settings.models.story_model, temperature=0.7, max_tokens=16384)
