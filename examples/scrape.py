"""Run a single scrape: python examples/scrape.py <url> <prompt>"""

import json
import sys

from lidi import scrape

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python examples/scrape.py <url> <prompt>")

    result = scrape(url=sys.argv[1], prompt=" ".join(sys.argv[2:]))
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
