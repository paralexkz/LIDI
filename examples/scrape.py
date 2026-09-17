"""Scrape one page and answer a question about it.

    uv run python examples/scrape.py <url> "<your question>"
    uv run python examples/scrape.py --schema company <url> "<your question>"

With --schema the output is constrained to a Pydantic model from
lidi.schemas (company, person) instead of free-form JSON.

Example:
    uv run python examples/scrape.py --schema company https://example.com/about \
        "Extract the company and its leadership team"
"""

from __future__ import annotations

import argparse
import json
import sys

from lidi import REGISTRY, MissingAPIKeyError, scrape


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="scrape.py",
        description="Scrape a page and answer a question about it.",
    )
    parser.add_argument("url", help="page to scrape")
    parser.add_argument("question", nargs="+", help="what to extract, in plain language")
    parser.add_argument(
        "--schema",
        choices=sorted(REGISTRY),
        help="constrain the output to this schema",
    )
    args = parser.parse_args()

    try:
        result = scrape(
            url=args.url,
            prompt=" ".join(args.question),
            schema=REGISTRY[args.schema] if args.schema else None,
        )
    except MissingAPIKeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if hasattr(result, "model_dump"):
        result = result.model_dump()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
