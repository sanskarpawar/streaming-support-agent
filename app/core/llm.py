"""
LLM provider factory — build_chat_service()

Selection logic (checked at call time, based on .env):
  1. OPENAI_API_KEY is set   → direct OpenAI  (OpenAIChatCompletion)
  2. APIM_BASE_URL is set    → Azure OpenAI via APIM proxy (AzureChatCompletion)
  3. fallback               → Azure OpenAI direct endpoint  (AzureChatCompletion)

The Azure path builds AsyncAzureOpenAI explicitly and injects it via async_client
so Semantic Kernel never reads AZURE_OPENAI_ENDPOINT from the environment (which
would override our APIM URL when both are set in .env).
"""
from __future__ import annotations

from openai import AsyncAzureOpenAI, AsyncOpenAI
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
)

from app.core.config import get_settings


def _build_azure_client(settings) -> AsyncAzureOpenAI:
    """Build an AsyncAzureOpenAI client.

    Priority:
      1. Direct Azure OpenAI endpoint  (when AZURE_OPENAI_ENDPOINT is set)
      2. APIM proxy                    (when only APIM_BASE_URL is set)

    Direct endpoint is preferred because APIM routing depends on policy
    configuration that may not cover all model deployments.
    """
    if settings.azure_openai_endpoint:
        return AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
    # Fallback: APIM proxy — subscription key in both api-key and
    # Ocp-Apim-Subscription-Key header (required by most APIM policies).
    return AsyncAzureOpenAI(
        azure_endpoint=settings.apim_base_url,
        api_key=settings.apim_subscription_key,
        api_version=settings.azure_openai_api_version,
        default_headers={
            "Ocp-Apim-Subscription-Key": settings.apim_subscription_key,
        },
    )


def build_chat_service() -> OpenAIChatCompletion | AzureChatCompletion:
    """Return the correct SK chat-completion service based on configured credentials."""
    settings = get_settings()

    if not settings.use_azure:
        # ── Direct OpenAI ──────────────────────────────────────────────────────
        return OpenAIChatCompletion(
            ai_model_id=settings.openai_model,
            api_key=settings.openai_api_key,
        )

    # ── Azure OpenAI — inject a fully built client so SK ignores env vars ─────
    azure_client = _build_azure_client(settings)
    return AzureChatCompletion(
        deployment_name=settings.azure_openai_chat_model,
        async_client=azure_client,
    )
