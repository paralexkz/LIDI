"""Run a schema-constrained scrape over many URLs and write a CSV.

Built for lists in the hundreds or thousands, so it assumes the run will be
interrupted: every row is flushed as it completes and an existing output file
is treated as progress to resume from. Failures are recorded as rows with a
``status`` rather than aborting the run — a single dead domain in a list of a
thousand must not cost you the other 999.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Type

from pydantic import BaseModel

from lidi.scraper import scrape

#: Columns written for every row, before the schema's own fields.
META_COLUMNS = ("url", "status", "error")


@dataclass
class BatchResult:
    """What a run did, for reporting."""

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0


def read_urls(path: str | Path) -> list[str]:
    """Read URLs from a text file (one per line) or a CSV with a ``url`` column.

    Blank lines and ``#`` comments are ignored, and duplicates are dropped
    while keeping the original order.
    """
    path = Path(path)
    raw: list[str] = []

    with path.open(newline="", encoding="utf-8") as handle:
        if path.suffix.lower() == ".csv":
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "url" not in reader.fieldnames:
                raise ValueError(f"{path} has no 'url' column")
            raw = [(row.get("url") or "").strip() for row in reader]
        else:
            raw = [line.strip() for line in handle]

    seen: set[str] = set()
    urls: list[str] = []
    for url in raw:
        if not url or url.startswith("#") or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def already_done(output: str | Path) -> set[str]:
    """URLs already present in a previous run's output, so they can be skipped."""
    path = Path(output)
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row.get("url") or "").strip()
            for row in csv.DictReader(handle)
            if (row.get("url") or "").strip()
        }


def flatten(url: str, data: Any, schema: Type[BaseModel]) -> Iterator[dict[str, Any]]:
    """Turn one scrape result into one or more CSV rows.

    A field holding a list of nested models (``Company.people``) is expanded
    into one row per entry, with the parent's fields repeated — the shape
    spreadsheets and CRMs expect.
    """
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    if not isinstance(data, dict):
        yield {"url": url, "status": "error", "error": f"unexpected result type: {type(data).__name__}"}
        return

    nested_field = None
    for name, field in schema.model_fields.items():
        value = data.get(name)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            nested_field = name
            break

    base = {"url": url, "status": "ok", "error": ""}
    scalars = {k: v for k, v in data.items() if k != nested_field and not isinstance(v, (list, dict))}

    children = data.get(nested_field) or [] if nested_field else []
    if not children:
        yield {**base, **scalars}
        return

    for child in children:
        prefixed = {f"{nested_field[:-1] if nested_field.endswith('s') else nested_field}_{k}": v
                    for k, v in child.items()}
        yield {**base, **scalars, **prefixed}


def columns_for(schema: Type[BaseModel]) -> list[str]:
    """Header for the output CSV, derived from the schema."""
    scalars: list[str] = []
    nested: list[str] = []
    for name, field in schema.model_fields.items():
        annotation = str(field.annotation)
        if "List[" in annotation or "list[" in annotation:
            inner = field.annotation.__args__[0] if getattr(field.annotation, "__args__", None) else None
            if inner is not None and hasattr(inner, "model_fields"):
                singular = name[:-1] if name.endswith("s") else name
                nested += [f"{singular}_{child}" for child in inner.model_fields]
                continue
        scalars.append(name)
    return [*META_COLUMNS, *scalars, *nested]


def run_batch(
    urls: Iterable[str],
    prompt: str,
    schema: Type[BaseModel],
    output: str | Path,
    resume: bool = True,
    delay: float = 0.0,
    on_progress=None,
) -> BatchResult:
    """Scrape every URL and append rows to ``output`` as they complete."""
    output = Path(output)
    urls = list(urls)
    done = already_done(output) if resume else set()
    header = columns_for(schema)
    result = BatchResult()

    write_header = not output.exists() or output.stat().st_size == 0
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        if write_header:
            writer.writeheader()

        for index, url in enumerate(urls, start=1):
            if url in done:
                result.skipped += 1
                continue

            result.attempted += 1
            try:
                data = scrape(url=url, prompt=prompt, schema=schema)
                rows = list(flatten(url, data, schema))
                result.succeeded += 1
                status = "ok"
            except Exception as exc:  # one bad URL must not end the run
                rows = [{"url": url, "status": "error", "error": f"{type(exc).__name__}: {exc}"[:500]}]
                result.failed += 1
                status = "error"

            for row in rows:
                writer.writerow(row)
            handle.flush()  # survive a crash mid-run

            if on_progress:
                on_progress(index, len(urls), url, status)
            if delay:
                time.sleep(delay)

    return result
