<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Changelog

All notable changes to exploradora are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). Nothing has been released yet.

## [Unreleased]

## [0.1.0] - 2026-08-11

### Added

- Package skeleton: `src/` layout, `exploradora` console script, dual-license
  layout (Apache-2.0 `core/`, AGPL-3.0-or-later elsewhere).
- RFC 8785 (JCS) canonical serialization, restricted to the integer domain
  (`exploradora.core.jcs`).
- Manifest schema v0 (`exploradora.core.manifest` + the `manifest.schema.json`
  interop artifact, kept in lockstep by test): frame tag with the one-way
  `parameterization` field, graded `verification` (never a boolean), an
  `oracle_basis` per claim, and `agreement_relation` per attestation.
  Identity = sha256 of the JCS serialization; a manifest never embeds its
  own hash.
- `exploradora verify`: manifest-schema + weights-integrity checks with the
  three-word vocabulary (`integrity-ok` / `integrity-failed` / `unchecked`);
  claims are reported unchecked, never silently skipped, and no overall
  verdict line exists.
- `exploradora init`: scaffolds a valid manifest for an existing weights
  file — hashes computed, authored facts required as flags (never guessed),
  claims start empty. Whatever init writes, verify accepts.
- The TUI: `exploradora` / `exploradora browse` — adapter table + manifest
  detail pane; every adapter starts `unchecked`; `v` verifies the selected
  one.
- `exploradora demo`: two deterministic sample adapters — one valid, one
  deliberately corrupted after manifest creation so verification has
  something real to catch. Sample weights are structurally valid
  safetensors written with the stdlib.
- Release tooling (agent half): `bump-version`, `release-check` (build,
  twine check, fresh-venv wheel install + suite + console-script smoke),
  `prepare-release` (stops at the human handoff), `tag-release` (human-run,
  GPG-signed). Index uploads remain human-only.
