"""Stderr logging for the GUI (optional ``--verbose`` / env)."""

from __future__ import annotations

import logging
import os
import sys
from typing import Sequence


_LOG = logging.getLogger("avell_storm_rgb.gui")


def env_verbose() -> bool:
    v = os.environ.get("AVELL_STORM_RGB_LOG", "").strip().lower()
    return v in ("1", "true", "yes", "debug", "verbose")


def strip_verbose_argv(argv: Sequence[str] | None) -> tuple[list[str], bool]:
    """Return ``(argv_for_qt, verbose)`` with GUI-only flags removed."""
    if argv is None:
        argv = sys.argv
    verbose = env_verbose()
    if not argv:
        return [], verbose
    out = [argv[0]]
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-v", "--verbose", "--debug"):
            verbose = True
            i += 1
            continue
        if a == "--":
            out.extend(argv[i:])
            break
        out.append(a)
        i += 1
    return out, verbose


def setup_logging(*, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    if not logging.root.handlers:
        logging.basicConfig(
            level=level,
            format="%(levelname)s %(name)s: %(message)s",
        )
    logging.getLogger().setLevel(level)


def log_usb_failure(exc: BaseException) -> str:
    """Log to stderr; full traceback when level is DEBUG. Returns text for the UI."""
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        _LOG.exception("USB worker task failed")
    else:
        _LOG.error("USB worker task failed: %s: %s", type(exc).__name__, exc)
    return f"{type(exc).__name__}: {exc}"
