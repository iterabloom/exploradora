# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command-line entry point for exploradora.

How it works: ``build_parser()`` constructs an ``argparse`` parser fresh per
invocation (no global state; tests inspect it directly). Subcommands are
registered **only for verbs that work** — currently ``verify`` — and the
pre-alpha status line names what is still under construction in roadmap
voice. ``main()`` dispatches and returns an exit code rather than calling
``sys.exit`` itself, so the same function serves the console script and
in-process tests.

``verify`` renders ``exploradora.core.verify.verify_dir()``'s sections as a
plain table, one row per concern, **with no overall verdict line**: the
honesty rules forbid an overall green while any section is unchecked, and in
v0.1 the claims section always is. The exit code is scripting-facing (0 iff
nothing failed and something was actually checked); the table is the human
truth.
"""

from __future__ import annotations

import argparse
from importlib.metadata import version as _dist_version
from pathlib import Path

from exploradora.core import verify as core_verify

#: One-line status, shown in --help. Roadmap voice, never feature voice.
_STATUS = (
    "pre-alpha: the manifest schema and `verify` work; the TUI and the "
    "init/demo commands are under construction and arrive as they become real."
)


def build_parser() -> argparse.ArgumentParser:
    """The CLI parser: subcommands exist only for verbs that are implemented."""
    parser = argparse.ArgumentParser(
        prog="exploradora",
        description="Local-first explorer for verifiable model adapters.",
        epilog=_STATUS,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_dist_version('exploradora')}",
    )
    sub = parser.add_subparsers(dest="command")
    p_verify = sub.add_parser(
        "verify",
        help="check an adapter directory: manifest schema + weights integrity",
        description=(
            "Checks manifest.json against schema v0 and the weights file's "
            "sha256 against the manifest. Reports each concern separately; "
            "claim replay is not implemented in v0.1 and is reported as "
            "unchecked, never silently skipped."
        ),
    )
    p_verify.add_argument("adapter_dir", type=Path, help="directory holding manifest.json")
    return parser


def _render(sections: tuple[core_verify.Section, ...]) -> str:
    """One row per concern, details indented beneath. Deliberately no summary row."""
    width = max(len(s.name) for s in sections)
    lines: list[str] = []
    for s in sections:
        lines.append(f"{s.name.ljust(width)}  {s.status}")
        lines.extend(f"{'':{width}}    {d}" for d in s.details)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point. Returns an exit code rather than calling exit()."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "verify":
        sections = core_verify.verify_dir(args.adapter_dir)
        print(_render(sections))
        return 0 if core_verify.ok_to_exit_zero(sections) else 1
    # No subcommand given: explain, succeed — nothing was asked, nothing failed.
    parser.print_help()
    return 0
