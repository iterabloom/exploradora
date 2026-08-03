<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# exploradora

**STATUS: pre-alpha — repository bootstrap in progress. Nothing is implemented
yet; nothing is published to PyPI yet.**

Exploradora will be a local-first terminal UI for exploring, verifying, and
managing small model adapters. The v0.1 goal is a local adapter-library
explorer: browse adapters on your own disk, inspect their manifests, and check
weights-file integrity against those manifests. No network code, no p2p, no
model inference in v0.1.

What exists right now: project governance, licensing, and CI scaffolding.
Missing: everything else — the package, the TUI, the manifest schema, the
verifier, the tests.

See `LICENSING.md` for the repository's dual-license layout. A `VISION.md`
describing the long-term thesis will arrive with the v0.1 implementation.
