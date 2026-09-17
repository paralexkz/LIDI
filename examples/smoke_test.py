"""Offline check that ScrapeGraphAI is installed and a graph can be built.

Makes no network calls. For a fuller report — including a real page load and
whether the model server is up — run examples/doctor.py instead.
"""

from importlib.metadata import version

from scrapegraphai.graphs import SmartScraperGraph

from lidi import build_config, find_chromium
from lidi.providers import api_key_env

if __name__ == "__main__":
    config = build_config()
    model = config["llm"]["model"]
    env_var = api_key_env(model)
    has_key = bool(config["llm"].get("api_key"))

    # Hosted providers refuse to build without credentials; a placeholder keeps
    # this an install check rather than a credentials check.
    llm = dict(config["llm"])
    if env_var and not has_key:
        llm["api_key"] = "placeholder"

    graph = SmartScraperGraph(
        prompt="What is this page about?",
        source="https://example.com",
        config={**config, "llm": llm},
    )
    print(f"scrapegraphai: {version('scrapegraphai')}")
    print(f"graph built:   {type(graph).__name__}")
    print(f"model:         {model}")
    print(f"chromium:      {find_chromium() or 'Playwright default build'}")
    if env_var:
        print(f"{env_var}: {'set' if has_key else 'MISSING — add it to .env'}")
    else:
        print(f"credentials:   none needed for this provider")
