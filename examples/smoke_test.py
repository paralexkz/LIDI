"""Offline check that ScrapeGraphAI is installed and a graph can be built.

Makes no network calls and needs no API key. For a fuller report — including a
real page load — run examples/doctor.py instead.
"""

from importlib.metadata import version

from scrapegraphai.graphs import SmartScraperGraph

from lidi import build_config, find_chromium

if __name__ == "__main__":
    config = build_config()
    has_key = bool(config["llm"]["api_key"])
    if not has_key:
        config["llm"]["api_key"] = "sk-placeholder"

    graph = SmartScraperGraph(
        prompt="What is this page about?",
        source="https://example.com",
        config=config,
    )
    print(f"scrapegraphai: {version('scrapegraphai')}")
    print(f"graph built:   {type(graph).__name__}")
    print(f"model:         {config['llm']['model']}")
    print(f"chromium:      {find_chromium() or 'Playwright default build'}")
    print(f"api key set:   {has_key}")
    if not has_key:
        print("\nSet OPENAI_API_KEY in .env before running examples/scrape.py")
