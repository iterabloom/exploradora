# SPDX-License-Identifier: AGPL-3.0-or-later
"""The adapter browser: a table of what is on disk, a pane of what it claims.

How it works: ``AdapterBrowser`` scans one library directory at construction
and renders a row per adapter (name, version, frame tag, size, status) beside
a detail pane showing the full manifest — or, for a directory whose manifest
could not be loaded, the load error, because a broken adapter the user cannot
see is worse than an ugly row. Every status starts as ``unchecked``:
scanning READS, only the ``v`` keybinding VERIFIES (running the same
``core.verify.verify_dir`` as the CLI), and the row then shows
``status_summary()``'s compressed verdict while the pane shows every section
in full. The summary never emits an overall green while any section is
unchecked — in v0.1 a fully passing adapter reads ``integrity-ok · claims
unchecked``, which is the no-overall-green honesty rule as a rendering rule.

``run_browser()`` is the one-line blocking entry point the CLI calls; the
app logic is exercised headless through Textual's ``run_test`` pilot.
"""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Static

from exploradora import library
from exploradora.core import verify

#: Column index of the status cell (name, version, frame, size, status).
STATUS_COLUMN = 4


def status_summary(sections: tuple[verify.Section, ...]) -> str:
    """One-cell verdict honoring the three-word vocabulary and no-overall-green."""
    statuses = [s.status for s in sections]
    if verify.STATUS_FAILED in statuses:
        return "integrity-failed"
    if verify.STATUS_OK not in statuses:
        return "unchecked"
    unchecked = [s.name for s in sections if s.status == verify.STATUS_UNCHECKED]
    if unchecked:
        return "integrity-ok · " + ", ".join(unchecked) + " unchecked"
    return "integrity-ok"


def detail_text(entry: library.Entry) -> str:
    """The detail pane's content: the manifest itself, or why it would not load."""
    if entry.load_error is not None:
        return f"{entry.path.name}\n\nmanifest could not be loaded:\n{entry.load_error}"
    return json.dumps(entry.manifest, indent=2, ensure_ascii=False)


def sections_text(sections: tuple[verify.Section, ...]) -> str:
    """Every verification section in full — the pane never compresses a verdict."""
    lines = []
    for s in sections:
        lines.append(f"{s.name}: {s.status}")
        lines.extend(f"  {d}" for d in s.details)
    return "\n".join(lines)


class AdapterBrowser(App[None]):
    """Browse one library directory; `v` verifies the selected adapter."""

    TITLE = "exploradora"
    CSS = """
    DataTable { width: 3fr; }
    #detail { width: 2fr; padding: 0 1; overflow-y: auto; border-left: solid $accent; }
    #empty { padding: 1 2; }
    """
    BINDINGS = [("v", "verify", "verify selected"), ("q", "quit", "quit")]

    def __init__(self, library_dir: Path) -> None:
        super().__init__()
        self.library_dir = library_dir
        self.entries = library.scan_library(library_dir)

    def compose(self) -> ComposeResult:
        yield Header()
        if self.entries:
            with Horizontal():
                yield DataTable()
                yield Static(id="detail")
        else:
            yield Static(
                f"no adapters found in {self.library_dir}\n\n"
                "an adapter is a directory holding a weights file and a manifest.json —\n"
                "make one explorable with `exploradora init <dir>`, or try the sample\n"
                "library: `exploradora demo`",
                id="empty",
            )
        yield Footer()

    def on_mount(self) -> None:
        if not self.entries:
            return
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("name", "version", "frame", "size", "status")
        for entry in self.entries:
            doc = entry.manifest
            if doc is None:
                row = (entry.path.name, "—", "—", library.format_size(entry.weights_size))
            else:
                row = (
                    doc["name"],
                    doc["version"],
                    library.frame_summary(doc),
                    library.format_size(entry.weights_size),
                )
            table.add_row(*row, "unchecked")
        table.focus()
        self._show_entry(0)

    def _show_entry(self, index: int) -> None:
        self.query_one("#detail", Static).update(detail_text(self.entries[index]))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_entry(event.cursor_row)

    def action_verify(self) -> None:
        if not self.entries:
            return
        table = self.query_one(DataTable)
        row = table.cursor_row
        entry = self.entries[row]
        sections = verify.verify_dir(entry.path)
        table.update_cell_at(Coordinate(row, STATUS_COLUMN), status_summary(sections))
        self.query_one("#detail", Static).update(
            detail_text(entry) + "\n\n" + sections_text(sections)
        )


def run_browser(library_dir: Path) -> None:
    """Run the blocking terminal app; the CLI's launch point."""
    AdapterBrowser(library_dir).run()  # pragma: no cover — interactive terminal loop; the app is covered headless via run_test pilots
