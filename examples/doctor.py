"""Check every part of the scraping chain and report what works.

    uv run python examples/doctor.py           # offline checks only
    uv run python examples/doctor.py --fetch   # also load a real page

Needs no API key: it verifies the machine, not your credentials.
"""

from __future__ import annotations

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

    config = build_config()

    # The graph refuses to build without credentials, so use a placeholder:
    # this checks the LLM wiring, not the key itself.
    has_key = bool(config["llm"]["api_key"])
    probe = {**config, "llm": {**config["llm"], "api_key": config["llm"]["api_key"] or "sk-placeholder"}}
    try:
        SmartScraperGraph(prompt="ping", source="https://example.com", config=probe)
        check("LLM config valid", True, f"model {config['llm']['model']}")
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

    check("OPENAI_API_KEY set", has_key, "" if has_key else "add it to .env before scraping")

    print()
    if _ok:
        print("Everything checks out. Run a scrape with:")
        print('  uv run python examples/scrape.py <url> "<your question>"')
    else:
        print("Some checks failed — see README.md > Troubleshooting.")
    return 0 if _ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
