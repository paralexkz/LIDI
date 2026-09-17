"""Check every part of the scraping chain and report what works.

    uv run python examples/doctor.py           # offline checks only
    uv run python examples/doctor.py --fetch   # also load a real page

Needs no API key: it verifies the machine, not your credentials.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import version

TEST_URL = "https://pypi.org/project/scrapegraphai/"

_ok = True


def check(label: str, passed: bool, detail: str = "") -> None:
    global _ok
    if not passed:
        _ok = False
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("LIDI environment check\n")

    py = sys.version_info
    check(
        "Python >= 3.12",
        py >= (3, 12),
        f"running {py.major}.{py.minor}.{py.micro}",
    )

    try:
        from scrapegraphai.graphs import SmartScraperGraph

        check("scrapegraphai import", True, f"version {version('scrapegraphai')}")
    except Exception as exc:
        check("scrapegraphai import", False, str(exc))
        return 1

    from lidi import build_config, find_chromium

    try:
        chromium = find_chromium()
        check(
            "Chromium found",
            True,
            chromium or "Playwright's own build",
        )
    except Exception as exc:
        check("Chromium found", False, str(exc))
        chromium = None

    from lidi.providers import KEYLESS, api_key_env, split_model

    config = build_config()
    model = config["llm"]["model"]
    provider = split_model(model)[0]
    env_var = api_key_env(model)
    has_key = bool(config["llm"].get("api_key"))

    # Providers refuse to build without credentials, so use a placeholder here:
    # this checks the LLM wiring, not the key itself.
    probe_llm = dict(config["llm"])
    if env_var and not has_key:
        probe_llm["api_key"] = "placeholder"
    try:
        SmartScraperGraph(
            prompt="ping", source="https://example.com", config={**config, "llm": probe_llm}
        )
        check("LLM config valid", True, f"model {model}")
    except Exception as exc:
        check("LLM config valid", False, str(exc))

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            kwargs = {"executable_path": chromium} if chromium else {}
            browser = p.chromium.launch(headless=True, **kwargs)
            page = browser.new_page()
            page.set_content("<h1>ok</h1>")
            launched = page.inner_text("h1") == "ok"
            browser.close()
        check("Chromium launches", launched)
    except Exception as exc:
        check("Chromium launches", False, str(exc).strip().splitlines()[0])

    if "--fetch" in sys.argv:
        try:
            from scrapegraphai.docloaders import ChromiumLoader

            loader = ChromiumLoader(
                [TEST_URL], backend="playwright", headless=True, **config.get("loader_kwargs", {})
            )
            text = loader.load()[0].page_content
            check("Live page fetch", len(text) > 0, f"{len(text)} chars from {TEST_URL}")
        except Exception as exc:
            check("Live page fetch", False, str(exc).strip().splitlines()[-1])
    else:
        print("[SKIP] Live page fetch — pass --fetch to test it")

    if provider in KEYLESS and provider == "ollama":
        base_url = config["llm"].get("base_url", "")
        try:
            import urllib.request

            with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as resp:
                models = json.loads(resp.read()).get("models", [])
            names = [m.get("name", "") for m in models]
            wanted = split_model(model)[1]
            installed = any(n == wanted or n.startswith(f"{wanted}:") for n in names)
            check("Ollama reachable", True, f"{base_url}, {len(names)} model(s)")
            check(
                f"Model '{wanted}' pulled",
                installed,
                "" if installed else f"run: ollama pull {wanted}",
            )
        except Exception as exc:
            check("Ollama reachable", False, f"{base_url} — {exc}. Is `ollama serve` running?")
    elif env_var:
        check(f"{env_var} set", has_key, "" if has_key else "add it to .env before scraping")

    print()
    if _ok:
        print("Everything checks out. Run a scrape with:")
        print('  uv run python examples/scrape.py <url> "<your question>"')
    else:
        print("Some checks failed — see README.md > Troubleshooting.")
    return 0 if _ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
