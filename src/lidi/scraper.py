"""Helpers for running ScrapeGraphAI's SmartScraperGraph."""

from __future__ import annotations

import os
from typing import Any, Type

from dotenv import load_dotenv
from pydantic import BaseModel

from lidi.browser import find_chromium

load_dotenv()

DEFAULT_MODEL = "openai/gpt-4o-mini"


class MissingAPIKeyError(RuntimeError):
    """Raised when no LLM credentials are configured."""


def build_config(model: str | None = None, **overrides: Any) -> dict[str, Any]:
    """Build a ScrapeGraphAI graph config.

    The API key is read from the environment so it never has to be passed
    around in code. ``model`` follows ScrapeGraphAI's ``provider/name`` form.

    A Chromium binary is discovered automatically and passed to Playwright as
    ``executable_path``; see :mod:`lidi.browser`.
    """
    config: dict[str, Any] = {
        "llm": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": model or os.environ.get("LIDI_MODEL", DEFAULT_MODEL),
        },
        "verbose": False,
        "headless": True,
    }

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
    if not llm.get("api_key") and "model_instance" not in llm:
        raise MissingAPIKeyError(
            "No LLM API key found. Copy .env.example to .env and set "
            "OPENAI_API_KEY=sk-... (or export it in your shell)."
        )

    graph = SmartScraperGraph(prompt=prompt, source=url, config=config, schema=schema)
    return graph.run()
