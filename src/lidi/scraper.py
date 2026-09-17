"""Helpers for running ScrapeGraphAI's SmartScraperGraph."""

from __future__ import annotations

import os
from typing import Any, Type

from dotenv import load_dotenv
from pydantic import BaseModel

from lidi.browser import find_chromium
from lidi.providers import KEYLESS, api_key_env, split_model

load_dotenv()

DEFAULT_MODEL = "ollama/llama3.1"

#: Where a local Ollama server listens, unless overridden.
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


class MissingAPIKeyError(RuntimeError):
    """Raised when no LLM credentials are configured."""


def build_config(model: str | None = None, **overrides: Any) -> dict[str, Any]:
    """Build a ScrapeGraphAI graph config.

    The model is written ``provider/name``; the provider decides which
    environment variable supplies the key, so switching providers is a matter
    of setting ``LIDI_MODEL``. Credentials are read from the environment and
    never passed around in code.

    A Chromium binary is discovered automatically and passed to Playwright as
    ``executable_path``; see :mod:`lidi.browser`.
    """
    model = model or os.environ.get("LIDI_MODEL", DEFAULT_MODEL)
    llm: dict[str, Any] = {"model": model}

    env_var = api_key_env(model)
    if env_var:
        llm["api_key"] = os.environ.get(env_var, "")

    if split_model(model)[0] == "ollama":
        llm["base_url"] = os.environ.get(
            "LIDI_OLLAMA_HOST", os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        )

    config: dict[str, Any] = {"llm": llm, "verbose": False, "headless": True}

    chromium = find_chromium()
    if chromium:
        config["loader_kwargs"] = {"executable_path": chromium}

    config.update(overrides)
    return config


def scrape(
    url: str,
    prompt: str,
    model: str | None = None,
    schema: Type[BaseModel] | None = None,
    **overrides: Any,
) -> Any:
    """Scrape ``url`` and answer ``prompt`` against its content.

    Args:
        schema: An optional Pydantic model. When given, the model is
            constrained to it and the result comes back with those fields;
            see :mod:`lidi.schemas`.

    Raises:
        MissingAPIKeyError: if no API key is configured and no ready-made
            ``model_instance`` was supplied.
    """
    from scrapegraphai.graphs import SmartScraperGraph

    config = build_config(model, **overrides)
    llm = config.get("llm", {})
    provider = split_model(llm.get("model", DEFAULT_MODEL))[0]

    needs_key = "model_instance" not in llm and provider not in KEYLESS
    if needs_key and not llm.get("api_key"):
        env_var = api_key_env(llm.get("model", DEFAULT_MODEL)) or "the provider's API key variable"
        raise MissingAPIKeyError(
            f"No API key found for provider '{provider}'. Copy .env.example to "
            f".env and set {env_var}=... (or export it in your shell)."
        )

    graph = SmartScraperGraph(prompt=prompt, source=url, config=config, schema=schema)
    return graph.run()
