"""Mapping ScrapeGraphAI providers to their credentials.

A model is written ``provider/name`` (``anthropic/claude-sonnet-4-5``), so the
provider prefix decides which environment variable holds the key and which
extra package has to be installed.
"""

from __future__ import annotations

#: Environment variable holding the API key, per provider.
API_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistralai": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "togetherai": "TOGETHER_API_KEY",
    "xai": "XAI_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
}

#: Providers that need no API key — they run locally or use ambient credentials.
KEYLESS = frozenset({"ollama", "bedrock", "google_vertexai"})

#: Extra packages required beyond what ScrapeGraphAI installs by default.
EXTRA_PACKAGE: dict[str, str] = {
    "anthropic": "langchain-anthropic",
    "google_genai": "langchain-google-genai",
    "google_vertexai": "langchain-google-vertexai",
    "groq": "langchain-groq",
    "fireworks": "langchain-fireworks",
    "togetherai": "langchain-together",
}


def split_model(model: str) -> tuple[str, str]:
    """Split ``provider/name`` into its two parts.

    A model without a prefix is assumed to be OpenAI's, matching
    ScrapeGraphAI's own fallback.
    """
    if "/" in model:
        provider, name = model.split("/", 1)
        return provider, name
    return "openai", model


def api_key_env(model: str) -> str | None:
    """The environment variable holding this model's key, or ``None`` if it needs none."""
    provider = split_model(model)[0]
    if provider in KEYLESS:
        return None
    return API_KEY_ENV.get(provider)
