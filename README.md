<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# exploradora

**STATUS: pre-alpha — the v0.1 surface works end to end: the TUI
(`exploradora` / `exploradora browse`), `verify`, `init`, and
`exploradora demo`. Nothing is published to PyPI yet; the exchange, p2p,
and claim replay are roadmap, not features.**

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
as unchecked — `exploradora init`, which scaffolds a valid manifest for an
existing weights file (hashes computed; authored facts required as flags,
never guessed; claims start empty), the TUI (`exploradora browse`; adapters
start `unchecked`, `v` verifies the selected one), and `exploradora demo` —
two deterministic sample adapters, one valid and one deliberately corrupted
after manifest creation, because a demo that only shows green would
demonstrate nothing.

See `LICENSING.md` for the repository's dual-license layout. A `VISION.md`
describing the long-term thesis will arrive with the v0.1 implementation.
