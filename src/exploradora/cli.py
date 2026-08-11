# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command-line entry point for exploradora.

How it works: a single ``argparse`` parser, built fresh per invocation by
``build_parser()`` so tests can construct and inspect it without touching
global state. ``main()`` parses ``argv``, and — because no subcommands exist
yet — its only jobs are ``--help``/``--version`` and an honest landing message
directing bare invocations to ``--help``.

Why this file exists before any feature does: the CI package gate installs the
built wheel into a fresh venv and smokes ``exploradora --help``, so the console
script must be real (not a stub that lies about features) from the first
release-shaped artifact. The help text states the pre-alpha status explicitly;
per AGENTS.md's honesty rules, subcommands appear here when they work, never
before.
"""

from __future__ import annotations

import argparse
from importlib.metadata import version as _dist_version

#: One-line status, shown in --help. Roadmap voice, never feature voice.
_STATUS = (
    "pre-alpha: package skeleton only. The v0.1 feature set (manifest schema, "
    "integrity verification, TUI, init/verify/demo) is under construction and "
    "arrives as it becomes real."
)


def build_parser() -> argparse.ArgumentParser:
    """The CLI parser: name, version, honest status text, no subcommands yet."""
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point. Returns an exit code rather than calling exit().

    ``argv=None`` means ``sys.argv[1:]`` (the argparse default), so the
    installed script behaves normally while tests pass explicit argv lists.
    """
    parser = build_parser()
    parser.parse_args(argv)
    # No subcommands exist yet, so a bare invocation gets the help text and a
    # success code: nothing was asked, nothing failed.
    parser.print_help()
    return 0
