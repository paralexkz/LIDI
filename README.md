# LIDI

Web scraping built on [ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai):
you give it a URL and a question in plain language, it loads the page in a real
browser and returns structured data.

## Requirements

- Python 3.12+ — ScrapeGraphAI 2.x requires `>=3.12,<4.0`
- [uv](https://docs.astral.sh/uv/)
- An OpenAI API key

## Install

```bash
uv python install 3.12          # only if you don't have 3.12 yet
uv sync                         # installs everything, incl. ScrapeGraphAI 2.2.4
uv run playwright install chromium
```

## Configure

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
OPENAI_API_KEY=sk-...
```

`.env` is git-ignored, so the key never gets committed. Optional settings
(`LIDI_MODEL`, `LIDI_CHROMIUM_PATH`) are documented in `.env.example`.

## Check the setup

```bash
uv run python examples/doctor.py --fetch
```

This verifies each link in the chain — Python version, ScrapeGraphAI import,
Chromium discovery, LLM config, browser launch, and a real page load — and says
which part is broken if any. It needs no API key.

## Run a scrape

```bash
uv run python examples/scrape.py <url> "<your question>"
```

For example:

```bash
uv run python examples/scrape.py https://pypi.org/project/scrapegraphai/ \
    "What is this project and what is it used for?"
```

The result is printed as JSON.

In code:

```python
from lidi import scrape

result = scrape(
    url="https://scrapegraphai.com",
    prompt="List the main features described on this page",
)
```

## Tests

```bash
uv run pytest                          # offline tests
LIDI_LIVE_TESTS=1 uv run pytest        # also loads a real page
```

## Layout

```
src/lidi/scraper.py   scrape() and build_config()
src/lidi/browser.py   finds a usable Chromium binary
examples/doctor.py    environment check
examples/scrape.py    command-line scraper
examples/smoke_test.py  quick offline install check
tests/                test suite
```

## Troubleshooting

### `No LLM API key found`

`.env` is missing or `OPENAI_API_KEY` is empty. `cp .env.example .env` and put
your key in it.

### `Looks like Playwright was just installed or updated... run playwright install`

Playwright only launches the exact Chromium build it ships with, and that build
is missing. Normally:

```bash
uv run playwright install chromium
```

If that download is blocked (offline machine, corporate network, restricted
container), LIDI falls back to any Chromium already on the system. Point it at
one explicitly if auto-detection picks the wrong binary:

```
LIDI_CHROMIUM_PATH=/usr/bin/chromium
```

### `net::ERR_CERT_AUTHORITY_INVALID`

Something is intercepting TLS — usually a corporate proxy — and Chromium does
not trust its certificate authority. Chromium does not read `SSL_CERT_FILE` or
`REQUESTS_CA_BUNDLE`; it uses its own NSS store, so the CA has to be imported
there:

```bash
sudo apt-get install -y libnss3-tools
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n corp-proxy-ca -i /path/to/proxy-ca.crt
```

Do not disable certificate verification to get around this.

### `net::ERR_TUNNEL_CONNECTION_FAILED`

The proxy refused to open a tunnel to that host — typically an egress allowlist
rather than a problem with the site. Check whether the host is permitted on
your network.

### `ProxyError ... openaipublic.blob.core.windows.net`

`tiktoken` downloads its tokenizer data on first use and that host is
unreachable. It is cached afterwards, so this only affects the first run on a
restricted network. Allow the host, or run the first scrape from a network that
permits it.
