"""Helpers for running ScrapeGraphAI's SmartScraperGraph."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "openai/gpt-4o-mini"


def build_config(model: str | None = None, **overrides: Any) -> dict[str, Any]:
    """Build a ScrapeGraphAI graph config.

    The API key is read from the environment so it never has to be passed around
    in code. ``model`` follows ScrapeGraphAI's ``provider/name`` form.

    If ``LIDI_CHROMIUM_PATH`` is set it is handed to Playwright's ``launch()``
    as ``executable_path``, which is how you point at a Chromium that is already
    on the machine instead of one Playwright downloaded itself.
    """
    config: dict[str, Any] = {
        "llm": {
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": model or os.environ.get("LIDI_MODEL", DEFAULT_MODEL),
        },
        "verbose": False,
        "headless": True,
    }

    chromium_path = os.environ.get("LIDI_CHROMIUM_PATH")
    if chromium_path:
        config["loader_kwargs"] = {"executable_path": chromium_path}

    config.update(overrides)
    return config


def scrape(
    url: str,
    prompt: str,
    model: str | None = None,
    **overrides: Any,
) -> Any:
    """Scrape ``url`` and answer ``prompt`` against its content."""
    from scrapegraphai.graphs import SmartScraperGraph

    graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=build_config(model, **overrides),
    )
    return graph.run()
