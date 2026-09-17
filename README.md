# LIDI

Web scraping workspace built on [ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai) —
an LLM-driven scraping library that turns a plain-language prompt plus a URL into
structured data.

## Requirements

- Python 3.12+ (ScrapeGraphAI 2.x requires `>=3.12,<4.0`)
- An API key for whichever LLM provider you use (OpenAI by default)

## Install

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync
uv run playwright install chromium   # browser backend used by the scraping loaders
```

Using pip:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

## Configure

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=sk-...
```

## Usage

```bash
uv run python examples/smoke_test.py          # offline check: imports + graph construction
uv run python examples/scrape.py https://scrapegraphai.com "What does this company do?"
```

In code:

```python
from lidi import scrape

result = scrape(
    url="https://scrapegraphai.com",
    prompt="List the main features described on this page",
)
print(result)
```

## Layout

```
src/lidi/          package code (thin wrapper over ScrapeGraphAI)
examples/          runnable scripts
pyproject.toml     dependencies
```

## Troubleshooting

**`Looks like Playwright was just installed or updated... run playwright install`**

The installed `playwright` package and the Chromium build on disk must match.
Running `playwright install chromium` inside this project's environment fetches
the matching build:

```bash
uv run playwright install chromium
```

If you already have a suitable Chromium and don't want a second copy, point at
it instead — LIDI forwards this to Playwright's `launch(executable_path=...)`:

```bash
LIDI_CHROMIUM_PATH=/path/to/chrome uv run python examples/scrape.py <url> <prompt>
```

**`net::ERR_TUNNEL_CONNECTION_FAILED`**

The headless browser can't reach the network — usually a proxy that intercepts
TLS with a CA the browser doesn't trust. Scraping needs direct outbound access
from the browser process, not just from Python.
