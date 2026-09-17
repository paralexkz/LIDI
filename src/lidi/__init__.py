"""LIDI — a thin wrapper around ScrapeGraphAI."""

from lidi.browser import find_chromium
from lidi.scraper import MissingAPIKeyError, build_config, scrape

__all__ = ["build_config", "find_chromium", "scrape", "MissingAPIKeyError"]
__version__ = "0.1.0"
