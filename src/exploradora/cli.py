# SPDX-License-Identifier: AGPL-3.0-or-later
"""Command-line entry point for exploradora.

How it works: ``build_parser()`` constructs an ``argparse`` parser fresh per
invocation (no global state; tests inspect it directly). Subcommands are
registered **only for verbs that work** — ``verify``, ``init``, ``browse``,
``demo`` — and the pre-alpha status line keeps unbuilt territory in roadmap
voice. ``main()`` dispatches and returns an exit code rather than calling
``sys.exit`` itself, so the same function serves the console script and
in-process tests. Bare ``exploradora`` opens the browser on the default
library — the TUI is the no-args experience per the v0.1 brief. The
``textual`` import happens lazily inside the browse path so that scripting
verbs (``verify``/``init``) never pay the TUI's startup cost.

``verify`` renders ``exploradora.core.verify.verify_dir()``'s sections as a
plain table, one row per concern, **with no overall verdict line**: the
honesty rules forbid an overall green while any section is unchecked, and in
v0.1 the claims section always is. The exit code is scripting-facing (0 iff
nothing failed and something was actually checked); the table is the human
truth.

``init`` scaffolds ``manifest.json`` for an existing weights file via
``exploradora.core.scaffold``. The flag surface mirrors the honesty split:
authored facts (frame tag, tokenizer hash, license) are REQUIRED — init
never guesses them — while ``--generator-class`` may default because the
schema carries an explicit ``unknown`` member for exactly this. Errors go to
stderr and exit 1 with nothing written.
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version as _dist_version
from pathlib import Path

from exploradora import demo as client_demo
from exploradora import library as client_library
from exploradora.core import manifest as core_manifest
from exploradora.core import scaffold as core_scaffold
from exploradora.core import verify as core_verify

#: One-line status, shown in --help. Roadmap voice, never feature voice.
_STATUS = (
    "pre-alpha: a local adapter-library explorer — the TUI (browse), verify, "
    "init, and demo work; nothing is published to PyPI yet. The exchange, "
    "p2p, and claim replay are roadmap, not features."
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

    p_init = sub.add_parser(
        "init",
        help="scaffold manifest.json for an existing weights file",
        description=(
            "Computes the weights sha256 and writes a valid manifest.json into "
            "the adapter directory, with EMPTY claims and attestations (no claim "
            "exists until something checked it). Authored facts — the frame tag, "
            "the tokenizer hash, the license — are required flags: init never "
            "guesses them. Refuses to overwrite an existing manifest."
        ),
    )
    p_init.add_argument("adapter_dir", type=Path, help="directory holding the weights file")
    p_init.add_argument("--name", help="adapter name (default: the directory's name)")
    p_init.add_argument(
        "--version", dest="adapter_version", metavar="VERSION",
        help=f"adapter version (default: {core_scaffold.DEFAULT_VERSION!r}, meaning unreleased)",
    )
    p_init.add_argument("--base-model", required=True, help="base model the adapter targets")
    p_init.add_argument("--a0-seed", required=True, type=int, help="frozen A0 down-projection seed")
    p_init.add_argument("--rank", required=True, type=int, help="adapter rank")
    p_init.add_argument(
        "--parameterization", required=True, choices=core_manifest.PARAMETERIZATIONS,
        help="adapter parameterization (load-bearing: lora converts to dora, never back)",
    )
    tok = p_init.add_mutually_exclusive_group(required=True)
    tok.add_argument("--tokenizer", type=Path, help="tokenizer file to hash")
    tok.add_argument("--tokenizer-sha256", help="tokenizer sha256, if already known")
    p_init.add_argument("--license", required=True, help="license of the adapter weights (SPDX)")
    p_init.add_argument(
        "--generator-class", choices=core_manifest.GENERATOR_CLASSES, default="unknown",
        help="who/what trained it (default: the schema's explicit 'unknown')",
    )
    p_init.add_argument(
        "--training-data", default="unspecified",
        help="free-text description of the training data (default: 'unspecified')",
    )
    p_init.add_argument(
        "--weights", metavar="FILENAME",
        help="weights filename inside the directory (default: the sole candidate)",
    )

    p_browse = sub.add_parser(
        "browse",
        help="open the TUI on an adapter library directory",
        description=(
            "Scans the library directory for adapter subdirectories (weights "
            "file + manifest.json) and opens the browser: a table of adapters "
            "with a manifest detail pane; press `v` to verify the selected "
            "one. Every adapter starts as `unchecked` — scanning reads, only "
            "verification verifies."
        ),
    )
    p_browse.add_argument(
        "library_dir", nargs="?", type=Path, default=None,
        help=f"library to scan (default: {client_library.DEFAULT_LIBRARY_DIR})",
    )

    p_demo = sub.add_parser(
        "demo",
        help="build the sample library and open the TUI on it",
        description=(
            "Creates two deterministic sample adapters — one valid, one with "
            "weights deliberately corrupted after its manifest was written, so "
            "verification has something real to catch — and opens the browser "
            "on them. The sample weights are structurally valid safetensors "
            "but NOT trained adapters, and their manifests say so."
        ),
    )
    p_demo.add_argument(
        "--library", type=Path, default=None,
        help=f"where to build the sample library (default: {client_demo.DEFAULT_DEMO_DIR})",
    )
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
    if args.command == "init":
        return _run_init(args)
    if args.command == "browse":
        return _run_browse(args.library_dir)
    if args.command == "demo":
        target = args.library if args.library is not None else client_demo.DEFAULT_DEMO_DIR
        client_demo.build_demo_library(target)
        return _run_browse(target)
    # No subcommand: the TUI on the default library is the no-args experience.
    return _run_browse(None)


def _run_browse(library_dir: Path | None) -> int:
    from exploradora import tui  # deferred: scripting verbs never pay textual's import cost

    tui.run_browser(library_dir if library_dir is not None else client_library.DEFAULT_LIBRARY_DIR)
    return 0


def _run_init(args: argparse.Namespace) -> int:
    """The init verb: resolve the tokenizer hash, scaffold, report or fail loudly."""
    if args.tokenizer is not None:
        if not args.tokenizer.is_file():
            print(f"tokenizer file not found: {args.tokenizer}", file=sys.stderr)
            return 1
        tokenizer_sha256 = core_verify.sha256_file(args.tokenizer)
    else:
        tokenizer_sha256 = args.tokenizer_sha256
    try:
        _doc, ident = core_scaffold.scaffold(
            args.adapter_dir,
            name=args.name,
            version=args.adapter_version,
            base_model=args.base_model,
            a0_seed=args.a0_seed,
            rank=args.rank,
            parameterization=args.parameterization,
            tokenizer_sha256=tokenizer_sha256,
            generator_class=args.generator_class,
            training_data=args.training_data,
            license=args.license,
            weights_filename=args.weights,
        )
    except core_scaffold.ScaffoldError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"wrote {args.adapter_dir / core_verify.MANIFEST_FILENAME}")
    print(f"identity {ident}")
    print(f"next: exploradora verify {args.adapter_dir}")
    return 0
