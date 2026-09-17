# LIDI

Web scraping built on [ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai):
you give it a URL and a question in plain language, it loads the page in a real
browser and returns structured data.

## Requirements

- Python 3.12+ — ScrapeGraphAI 2.x requires `>=3.12,<4.0`
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com) running locally — the default, no API key needed.
  Any hosted provider works too; see *Using a hosted provider* below.

## Install

```bash
uv python install 3.12          # only if you don't have 3.12 yet
uv sync                         # installs everything, incl. ScrapeGraphAI 2.2.4
uv run playwright install chromium
```

Then the model, which runs on your own machine:

```bash
ollama pull llama3.1            # needs Ollama installed: https://ollama.com
ollama serve                    # skip if it already runs as a service
```

## Configure

Nothing is required — the defaults point at a local Ollama on
`http://localhost:11434`. To change the model or the host:

```bash
cp .env.example .env
```

`.env` is git-ignored, so nothing in it gets committed. Every setting
(`LIDI_MODEL`, `LIDI_OLLAMA_HOST`, `LIDI_CHROMIUM_PATH`, provider keys) is
documented there.

### Using a hosted provider

Set `LIDI_MODEL` to `provider/name` and supply that provider's key. LIDI picks
the right environment variable from the prefix:

| `LIDI_MODEL`                    | Key variable        |
| ------------------------------- | ------------------- |
| `ollama/llama3.1` *(default)*   | none — runs locally |
| `openai/gpt-4o-mini`            | `OPENAI_API_KEY`    |
| `anthropic/claude-sonnet-4-5`   | `ANTHROPIC_API_KEY` |
| `mistralai/mistral-small`       | `MISTRAL_API_KEY`   |

Anthropic and Google need one extra package (`uv add langchain-anthropic` or
`uv add langchain-google-genai`); OpenAI, Mistral and Ollama work out of the box.

## Check the setup

```bash
uv run python examples/doctor.py --fetch
```

This verifies each link in the chain — Python version, ScrapeGraphAI import,
Chromium discovery, LLM config, browser launch, a real page load, and whether
Ollama is up with your model pulled — and says which part is broken if any.

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

## Structured extraction

Passing a schema constrains the model to it, so you get the same fields every
time instead of whatever shape the model felt like returning:

```bash
uv run python examples/scrape.py --schema company https://example.com/about \
    "Extract the company and its leadership team"
```

```python
from lidi import Company, scrape

result = scrape(
    url="https://example.com/about",
    prompt="Extract the company and its leadership team",
    schema=Company,
)
```

`Company` collects the firm's name, website, jurisdiction and a list of
`Person` entries (name, role, LinkedIn URL). Optional fields come back as
`None` when the page does not state them — `jurisdiction`, for instance, is
only filled from an explicit legal notice or imprint, not inferred from an
office address.

Schemas live in `src/lidi/schemas.py`. Add your own by defining a Pydantic
model there and registering it in `REGISTRY` to expose it to `--schema`.

## Scraping a list of sites

For anything past a handful of pages, put the URLs in a file (one per line, or
a CSV with a `url` column) and run them as a batch:

```bash
uv run python examples/batch.py urls.txt --schema company -o companies.csv
```

The output has one row per person, with the company's fields repeated — the
shape spreadsheets and CRMs expect:

```
url,status,error,company_name,website,jurisdiction,people_full_name,people_role,people_linkedin_url
```

Built for long lists, so it assumes the run will be interrupted:

- every row is flushed as it completes, so a crash keeps what it had
- re-running skips URLs already in the output (`--no-resume` to force)
- a URL that fails is written with `status=error` and the reason, and the run
  continues — one dead domain does not cost you the rest
- `--delay 1` spaces out requests; `--limit 20` tries a slice first

Always start with `--limit 20` on a new list: it shows whether the schema and
prompt actually fit those pages before you spend hours and tokens on the rest.

## Tests

```bash
uv run pytest                          # offline tests
LIDI_LIVE_TESTS=1 uv run pytest        # also loads a real page
```

## Layout

```
src/lidi/scraper.py   scrape() and build_config()
src/lidi/schemas.py   Pydantic schemas for structured extraction
src/lidi/providers.py provider -> credentials mapping
src/lidi/browser.py   finds a usable Chromium binary
src/lidi/batch.py     batch runs over a list of URLs
examples/doctor.py    environment check
examples/scrape.py    command-line scraper
examples/batch.py     batch CLI
examples/smoke_test.py  quick offline install check
tests/                test suite
```

## Troubleshooting

### `Ollama reachable — Connection refused`

The local model server is not running. Start it with `ollama serve`, or point
`LIDI_OLLAMA_HOST` at wherever it listens.

### `Model 'llama3.1' pulled — FAIL`

The model is not downloaded yet: `ollama pull llama3.1`.

### `No API key found for provider '...'`

You switched `LIDI_MODEL` to a hosted provider. Set that provider's key in
`.env` — the table above says which variable.

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

ScrapeGraphAI counts tokens with `tiktoken`, which downloads its vocabulary on
first use — it does this **for every provider, including local Ollama**, so the
first run needs access to that host even when nothing else leaves your machine.
It is cached afterwards.
