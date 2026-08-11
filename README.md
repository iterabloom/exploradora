<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# exploradora

**STATUS: pre-alpha — governance, licensing, CI scaffolding, and the package
skeleton (installable, `exploradora --help`/`--version` only) are in place;
no features are implemented, and nothing is published to PyPI.**

Exploradora will be a local-first terminal UI for exploring, verifying, and
managing small model adapters. The v0.1 goal is a local adapter-library
explorer: browse adapters on your own disk, inspect their manifests, and check
weights-file integrity against those manifests. No network code, no p2p, no
model inference in v0.1.

What exists right now: project governance (AGENTS.md, CODEOWNERS, git hooks),
the dual-license layout, PR automation, a Woodpecker CI gate, and the package
skeleton — `pyproject.toml`, a console script whose only verbs are `--help`
and `--version`, and its tests. Missing: every feature — the manifest schema,
the verifier, the TUI, `init`/`verify`/`demo`.

See `LICENSING.md` for the repository's dual-license layout. A `VISION.md`
describing the long-term thesis will arrive with the v0.1 implementation.
