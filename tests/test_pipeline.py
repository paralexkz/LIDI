"""Tests for the LIDI scraping chain.

The fast tests run offline. The ones that touch the network are opt-in:

    LIDI_LIVE_TESTS=1 uv run pytest
"""

from __future__ import annotations

import json
import os

import pytest

from lidi import MissingAPIKeyError, build_config, find_chromium, scrape

TEST_URL = "https://pypi.org/project/scrapegraphai/"

live_only = pytest.mark.skipif(
    os.environ.get("LIDI_LIVE_TESTS") != "1",
    reason="set LIDI_LIVE_TESTS=1 to run tests that load real pages",
)


def test_scrapegraphai_imports():
    from scrapegraphai.graphs import SmartScraperGraph  # noqa: F401


def test_build_config_defaults():
    config = build_config()
    assert config["headless"] is True
    assert "/" in config["llm"]["model"], "model should be in provider/name form"


def test_build_config_overrides_model():
    assert build_config("openai/gpt-4o")["llm"]["model"] == "openai/gpt-4o"


def test_chromium_is_available():
    """None means Playwright's own build is present, which is also fine."""
    chromium = find_chromium()
    if chromium is not None:
        assert os.path.exists(chromium)


def test_graph_builds_with_placeholder_key():
    from scrapegraphai.graphs import SmartScraperGraph

    config = build_config()
    config["llm"]["api_key"] = config["llm"]["api_key"] or "sk-placeholder"
    graph = SmartScraperGraph(prompt="ping", source=TEST_URL, config=config)
    assert graph is not None


def test_scrape_without_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        scrape(url=TEST_URL, prompt="anything")


def test_chromium_launches():
    from playwright.sync_api import sync_playwright

    chromium = find_chromium()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, **({"executable_path": chromium} if chromium else {})
        )
        page = browser.new_page()
        page.set_content("<h1>ok</h1>")
        assert page.inner_text("h1") == "ok"
        browser.close()


@live_only
def test_live_page_fetch():
    from scrapegraphai.docloaders import ChromiumLoader

    config = build_config()
    loader = ChromiumLoader(
        [TEST_URL], backend="playwright", headless=True, **config.get("loader_kwargs", {})
    )
    text = loader.load()[0].page_content
    assert len(text) > 1000
    assert "scrapegraphai" in text.lower()


@live_only
def test_full_pipeline_with_stub_llm():
    """URL -> Chromium -> ScrapeGraphAI -> LLM -> structured dict.

    A stub chat model stands in for the provider so the graph can be exercised
    without credentials or spend.
    """
    pytest.importorskip("langchain_community")
    import tiktoken

    try:
        tiktoken.encoding_for_model("gpt-4o")
    except Exception as exc:  # pragma: no cover - depends on network
        pytest.skip(f"tiktoken could not load its encoding: {exc}")

    from langchain_community.chat_models.fake import FakeListChatModel

    payload = json.dumps({"name": "scrapegraphai", "summary": "web scraping library"})
    stub = FakeListChatModel(responses=[payload] * 50)

    result = scrape(
        url=TEST_URL,
        prompt="Extract the project name and a one-line summary.",
        llm={"model_instance": stub, "model_tokens": 8192},
    )
    assert isinstance(result, dict)
    assert result["name"] == "scrapegraphai"


def test_person_defaults():
    from lidi import Person

    person = Person(full_name="Ada Lovelace")
    assert person.role is None
    assert person.linkedin_url is None


def test_company_defaults_to_empty_people():
    from lidi import Company

    company = Company(company_name="Acme")
    assert company.people == []
    assert company.jurisdiction is None


def test_company_parses_nested_people():
    from lidi import Company

    company = Company.model_validate(
        {
            "company_name": "Acme",
            "website": "acme.test",
            "people": [{"full_name": "Ada Lovelace", "role": "CTO"}],
        }
    )
    assert company.people[0].full_name == "Ada Lovelace"
    assert company.people[0].role == "CTO"


def test_company_requires_name():
    from pydantic import ValidationError

    from lidi import Company

    with pytest.raises(ValidationError):
        Company.model_validate({"website": "acme.test"})


def test_registry_exposes_schemas():
    from lidi import REGISTRY, Company, Person

    assert REGISTRY["company"] is Company
    assert REGISTRY["person"] is Person


def test_schema_reaches_the_graph():
    """A schema must be handed to the graph, not silently dropped."""
    from scrapegraphai.graphs import SmartScraperGraph

    from lidi import Company

    config = build_config()
    config["llm"]["api_key"] = config["llm"]["api_key"] or "sk-placeholder"
    graph = SmartScraperGraph(prompt="ping", source=TEST_URL, config=config, schema=Company)
    assert graph.schema is Company


@live_only
def test_full_pipeline_with_schema():
    """URL -> Chromium -> ScrapeGraphAI -> LLM -> schema-shaped result."""
    pytest.importorskip("langchain_community")
    import tiktoken

    try:
        tiktoken.encoding_for_model("gpt-4o")
    except Exception as exc:  # pragma: no cover - depends on network
        pytest.skip(f"tiktoken could not load its encoding: {exc}")

    from langchain_community.chat_models.fake import FakeListChatModel

    from lidi import Company

    payload = json.dumps(
        {
            "company_name": "ScrapeGraphAI",
            "website": "scrapegraphai.com",
            "jurisdiction": None,
            "people": [{"full_name": "Marco Vinciguerra", "role": "Founder"}],
        }
    )
    stub = FakeListChatModel(responses=[payload] * 50)

    result = scrape(
        url=TEST_URL,
        prompt="Extract the company and its people.",
        schema=Company,
        llm={"model_instance": stub, "model_tokens": 8192},
    )
    data = result.model_dump() if hasattr(result, "model_dump") else result
    assert data["company_name"] == "ScrapeGraphAI"
    assert data["people"][0]["full_name"] == "Marco Vinciguerra"
