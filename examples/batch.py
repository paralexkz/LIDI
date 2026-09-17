"""Scrape a list of URLs into a CSV.

    uv run python examples/batch.py urls.txt --schema company -o companies.csv

urls.txt holds one URL per line (a .csv with a `url` column also works).
The run can be interrupted and restarted: rows already in the output file are
skipped, and a URL that fails is recorded with an error instead of stopping
everything.
"""

from __future__ import annotations

import argparse
import sys

from lidi import REGISTRY, MissingAPIKeyError
from lidi.batch import read_urls, run_batch

DEFAULT_PROMPT = (
    "Extract the company described on this page and every named founder or "
    "executive. Leave a field empty rather than guessing."
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="batch.py", description="Scrape many URLs into a CSV."
    )
    parser.add_argument("urls_file", help="text file with one URL per line, or a CSV with a url column")
    parser.add_argument("-o", "--output", default="results.csv", help="CSV to write (default: results.csv)")
    parser.add_argument("--schema", default="company", choices=sorted(REGISTRY))
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--delay", type=float, default=0.0, help="seconds to wait between pages")
    parser.add_argument("--limit", type=int, help="only process the first N URLs")
    parser.add_argument("--no-resume", action="store_true", help="re-scrape URLs already in the output")
    args = parser.parse_args()

    urls = read_urls(args.urls_file)
    if args.limit:
        urls = urls[: args.limit]
    if not urls:
        print(f"error: no URLs found in {args.urls_file}", file=sys.stderr)
        return 2

    print(f"{len(urls)} URL(s) -> {args.output}\n")

    def progress(index: int, total: int, url: str, status: str) -> None:
        mark = "ok " if status == "ok" else "ERR"
        print(f"[{index}/{total}] {mark} {url}", flush=True)

    try:
        result = run_batch(
            urls=urls,
            prompt=args.prompt,
            schema=REGISTRY[args.schema],
            output=args.output,
            resume=not args.no_resume,
            delay=args.delay,
            on_progress=progress,
        )
    except MissingAPIKeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"\ndone: {result.succeeded} ok, {result.failed} failed, "
        f"{result.skipped} skipped (already done)"
    )
    print(f"written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
