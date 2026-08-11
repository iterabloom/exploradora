# SPDX-License-Identifier: AGPL-3.0-or-later
"""Library scanning: what adapters are on disk, before anything is verified.

How it works: ``scan_library()`` walks one directory level looking for
subdirectories that carry a ``manifest.json`` and returns an ``Entry`` per
adapter, sorted by directory name. Each entry records what could be *read* —
the parsed manifest (or the reason it could not be loaded) and the weights
file's size — and deliberately records no verification verdict: scanning is
cheap and runs on every launch, verification is a user action, and the
honesty rules require the two never blur. A directory whose manifest is
unparsable or schema-invalid still gets an entry (``manifest=None`` plus a
``load_error``) so the TUI can show the user what is broken instead of
silently hiding it; ``verify`` remains the authority on what the failure is.

The rendering helpers (``frame_summary``, ``format_size``) are pure
functions kept beside the data they render so the TUI stays a thin shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exploradora.core import jcs, manifest
from exploradora.core.verify import MANIFEST_FILENAME

#: Where the TUI looks when no path is given (spec: the local adapter library).
DEFAULT_LIBRARY_DIR = Path.home() / ".exploradora" / "library"


@dataclass(frozen=True)
class Entry:
    """One adapter directory as found on disk — read, never verified."""

    path: Path
    manifest: dict[str, Any] | None
    load_error: str | None
    weights_size: int | None


def _load_entry(adapter_dir: Path) -> Entry:
    try:
        doc = manifest.loads((adapter_dir / MANIFEST_FILENAME).read_bytes())
    except (jcs.JCSError, manifest.ManifestError) as exc:
        return Entry(adapter_dir, None, str(exc), None)
    errors = manifest.validate(doc)
    if errors:
        return Entry(
            adapter_dir,
            None,
            f"invalid manifest ({len(errors)} error(s)): " + "; ".join(errors),
            None,
        )
    weights_path = adapter_dir / doc["weights"]["filename"]
    size = weights_path.stat().st_size if weights_path.is_file() else None
    return Entry(adapter_dir, doc, None, size)


def scan_library(library_dir: Path) -> tuple[Entry, ...]:
    """All adapter directories under ``library_dir``, sorted by name."""
    if not library_dir.is_dir():
        return ()
    return tuple(
        _load_entry(child)
        for child in sorted(library_dir.iterdir())
        if child.is_dir() and (child / MANIFEST_FILENAME).is_file()
    )


def frame_summary(doc: dict[str, Any]) -> str:
    """The frame tag, one line: model, rank, parameterization."""
    frame = doc["frame"]
    return f"{frame['base_model']} · r{frame['rank']} · {frame['parameterization']}"


def format_size(n: int | None) -> str:
    """Human-readable decimal size; an em dash where the file was not found."""
    if n is None:
        return "—"
    if n < 1000:
        return f"{n} B"
    value = float(n)
    for unit in ("KB", "MB", "GB"):
        value /= 1000.0
        if value < 1000 or unit == "GB":
            return f"{value:.1f} {unit}"
    raise AssertionError("unreachable")  # pragma: no cover — loop always returns at GB
