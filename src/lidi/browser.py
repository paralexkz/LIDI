"""Locating a Chromium binary for Playwright.

Playwright only launches the exact build revision it was compiled against. When
that build is missing (offline machine, restricted network, a system Chromium
installed instead), ``playwright install chromium`` is the normal fix — but it
needs to reach Playwright's CDN. This module makes LIDI fall back to any
Chromium already present so scraping still works.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

#: Set this to skip discovery and use a specific binary.
ENV_VAR = "LIDI_CHROMIUM_PATH"

_SYSTEM_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
)


def _playwright_default() -> str | None:
    """The binary Playwright itself would use, if it is actually on disk."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = p.chromium.executable_path
    except Exception:
        return None
    return path if path and Path(path).exists() else None


def _bundled_chromium() -> str | None:
    """Any Chromium under PLAYWRIGHT_BROWSERS_PATH, newest build first."""
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not root or not Path(root).is_dir():
        return None

    def build_number(directory: Path) -> int:
        suffix = directory.name.rsplit("-", 1)[-1]
        return int(suffix) if suffix.isdigit() else 0

    # Prefer a full chromium build over headless_shell: the shell cannot run
    # headed mode and some sites behave differently against it.
    for prefix in ("chromium-", "chromium_headless_shell-"):
        dirs = sorted(
            (d for d in Path(root).iterdir() if d.is_dir() and d.name.startswith(prefix)),
            key=build_number,
            reverse=True,
        )
        for directory in dirs:
            for relative in ("chrome-linux/chrome", "chrome-linux64/chrome", "chrome-win/chrome.exe"):
                candidate = directory / relative
                if candidate.exists():
                    return str(candidate)
    return None


def _system_chromium() -> str | None:
    for name in _SYSTEM_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


def find_chromium() -> str | None:
    """Return a usable Chromium path, or ``None`` to let Playwright decide.

    ``None`` means Playwright's own build is present and correct, so no
    ``executable_path`` override is needed.
    """
    override = os.environ.get(ENV_VAR)
    if override:
        if not Path(override).exists():
            raise FileNotFoundError(f"{ENV_VAR} points at a missing file: {override}")
        return override

    if _playwright_default():
        return None

    return _bundled_chromium() or _system_chromium()
