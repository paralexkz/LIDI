"""Scrape one page and answer a question about it.

    uv run python examples/scrape.py <url> "<your question>"

Example:
    uv run python examples/scrape.py https://pypi.org/project/scrapegraphai/ \
        "What is this project and who maintains it?"
"""

from __future__ import annotations

import json
import sys

from lidi import MissingAPIKeyError, scrape

USAGE = 'usage: uv run python examples/scrape.py <url> "<your question>"'


def main() -> int:
    if len(sys.argv) < 3:
        print(USAGE, file=sys.stderr)
        return 2

    url, prompt = sys.argv[1], " ".join(sys.argv[2:])

    try:
        result = scrape(url=url, prompt=prompt)
    except MissingAPIKeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
