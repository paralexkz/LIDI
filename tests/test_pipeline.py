"""Tests for the LIDI scraping chain.

The fast tests run offline. The ones that touch the network are opt-in:

    LIDI_LIVE_TESTS=1 uv run pytest
"""

from __future__ import annotations

import csv
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


def test_graph_builds_with_default_provider():
    from scrapegraphai.graphs import SmartScraperGraph

    config = build_config()
    if "api_key" in config["llm"]:
        config["llm"]["api_key"] = config["llm"]["api_key"] or "placeholder"
    graph = SmartScraperGraph(prompt="ping", source=TEST_URL, config=config)
    assert graph is not None


def test_scrape_without_key_raises_for_hosted_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError) as excinfo:
        scrape(url=TEST_URL, prompt="anything", model="openai/gpt-4o-mini")
    assert "OPENAI_API_KEY" in str(excinfo.value)


def test_keyless_provider_does_not_require_a_key(monkeypatch):
    """Ollama runs locally, so a missing key must not block the call."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = build_config("ollama/llama3.1")
    assert "api_key" not in config["llm"]
    assert config["llm"]["base_url"].startswith("http")


def test_ollama_host_is_overridable(monkeypatch):
    monkeypatch.setenv("LIDI_OLLAMA_HOST", "http://example.test:1234")
    assert build_config("ollama/llama3.1")["llm"]["base_url"] == "http://example.test:1234"


def test_api_key_env_per_provider():
    from lidi.providers import api_key_env, split_model

    assert api_key_env("openai/gpt-4o-mini") == "OPENAI_API_KEY"
    assert api_key_env("anthropic/claude-sonnet-4-5") == "ANTHROPIC_API_KEY"
    assert api_key_env("ollama/llama3.1") is None
    assert split_model("gpt-4o-mini") == ("openai", "gpt-4o-mini")
    assert split_model("ollama/llama3.1") == ("ollama", "llama3.1")


def test_hosted_provider_reads_its_own_key(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    assert build_config("mistralai/mistral-small")["llm"]["api_key"] == "test-key"


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
    if "api_key" in config["llm"]:
        config["llm"]["api_key"] = config["llm"]["api_key"] or "placeholder"
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


def test_smoke_test_example_runs():
    """examples/smoke_test.py must work for keyless and hosted providers alike."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for model in ("ollama/llama3.1", "openai/gpt-4o-mini"):
        proc = subprocess.run(
            [sys.executable, str(root / "examples" / "smoke_test.py")],
            capture_output=True,
            text=True,
            env={**os.environ, "LIDI_MODEL": model},
            cwd=root,
        )
        assert proc.returncode == 0, f"{model}: {proc.stderr[-500:]}"
        assert "graph built" in proc.stdout


def test_scrape_example_shows_usage():
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [sys.executable, str(root / "examples" / "scrape.py"), "--help"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert proc.returncode == 0
    assert "--schema" in proc.stdout


# --- batch runs -------------------------------------------------------------


def _urls_file(tmp_path, lines):
    path = tmp_path / "urls.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_read_urls_skips_blanks_comments_and_duplicates(tmp_path):
    from lidi.batch import read_urls

    path = _urls_file(tmp_path, ["https://a.test", "", "# note", "https://a.test", "https://b.test"])
    assert read_urls(path) == ["https://a.test", "https://b.test"]


def test_read_urls_from_csv(tmp_path):
    from lidi.batch import read_urls

    path = tmp_path / "urls.csv"
    path.write_text("name,url\nAcme,https://a.test\nBeta,https://b.test\n", encoding="utf-8")
    assert read_urls(path) == ["https://a.test", "https://b.test"]


def test_columns_follow_the_schema():
    from lidi.batch import columns_for

    from lidi import Company

    cols = columns_for(Company)
    assert cols[:3] == ["url", "status", "error"]
    assert "company_name" in cols
    assert "people_full_name" in cols


def test_flatten_makes_one_row_per_person():
    from lidi.batch import flatten

    from lidi import Company

    rows = list(
        flatten(
            "https://a.test",
            {
                "company_name": "Acme",
                "website": "acme.test",
                "jurisdiction": None,
                "people": [
                    {"full_name": "Ada", "role": "CTO", "linkedin_url": None},
                    {"full_name": "Bob", "role": None, "linkedin_url": None},
                ],
            },
            Company,
        )
    )
    assert len(rows) == 2
    assert {r["people_full_name"] for r in rows} == {"Ada", "Bob"}
    assert all(r["company_name"] == "Acme" for r in rows)


def test_flatten_handles_a_company_with_no_people():
    from lidi.batch import flatten

    from lidi import Company

    rows = list(flatten("https://a.test", {"company_name": "Acme", "people": []}, Company))
    assert len(rows) == 1
    assert rows[0]["status"] == "ok"


def test_batch_records_failures_and_keeps_going(tmp_path, monkeypatch):
    """One dead URL must not cost the rest of the list."""
    import lidi.batch as batch_mod

    from lidi import Company

    def fake_scrape(url, prompt, schema=None, **kwargs):
        if "bad" in url:
            raise RuntimeError("boom")
        return {"company_name": f"Co-{url[-1]}", "people": []}

    monkeypatch.setattr(batch_mod, "scrape", fake_scrape)
    out = tmp_path / "out.csv"
    result = batch_mod.run_batch(
        ["https://a.test/1", "https://bad.test/2", "https://c.test/3"],
        prompt="x",
        schema=Company,
        output=out,
    )

    assert (result.succeeded, result.failed) == (2, 1)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 3
    errored = [r for r in rows if r["status"] == "error"]
    assert len(errored) == 1
    assert "boom" in errored[0]["error"]


def test_batch_resumes_and_skips_completed_urls(tmp_path, monkeypatch):
    import lidi.batch as batch_mod

    from lidi import Company

    calls: list[str] = []

    def fake_scrape(url, prompt, schema=None, **kwargs):
        calls.append(url)
        return {"company_name": "Co", "people": []}

    monkeypatch.setattr(batch_mod, "scrape", fake_scrape)
    out = tmp_path / "out.csv"
    urls = ["https://a.test", "https://b.test"]

    batch_mod.run_batch(urls, prompt="x", schema=Company, output=out)
    assert len(calls) == 2

    second = batch_mod.run_batch(urls + ["https://c.test"], prompt="x", schema=Company, output=out)
    assert second.skipped == 2
    assert second.succeeded == 1
    assert calls[-1] == "https://c.test"
