<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# exploradora

**STATUS: pre-alpha — the manifest schema, `exploradora verify`, and
`exploradora init` work; the TUI and `demo` are under construction, and
nothing is published to PyPI.**

Exploradora will be a local-first terminal UI for exploring, verifying, and
managing small model adapters. The v0.1 goal is a local adapter-library
explorer: browse adapters on your own disk, inspect their manifests, and check
weights-file integrity against those manifests. No network code, no p2p, no
model inference in v0.1.

What exists right now: project governance (AGENTS.md, CODEOWNERS, git hooks),
the dual-license layout, PR automation, a Woodpecker CI gate, the package
skeleton, the manifest schema (`exploradora.core.manifest` + its JSON Schema,
RFC 8785 canonical serialization, sha256 identity), `exploradora verify` —
manifest-schema and weights-integrity checks with claims explicitly reported
as unchecked — and `exploradora init`, which scaffolds a valid manifest for
an existing weights file (hashes computed; authored facts required as flags,
never guessed; claims start empty). Missing: the TUI and the `demo` command.

See `LICENSING.md` for the repository's dual-license layout. A `VISION.md`
describing the long-term thesis will arrive with the v0.1 implementation.
