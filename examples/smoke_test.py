"""Offline check that ScrapeGraphAI is installed and a graph can be built.

Makes no network calls. Falls back to a placeholder key when none is set, so it
verifies the install rather than your credentials.
"""

from importlib.metadata import version

from scrapegraphai.graphs import SmartScraperGraph

from lidi import build_config

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
    print(f"api key set:   {has_key}")
    if not has_key:
        print("\nSet OPENAI_API_KEY in .env before running examples/scrape.py")
