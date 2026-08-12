<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Changelog

All notable changes to exploradora are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `.github/workflows/release.yml` — the thing a pushed tag triggers. Until
  now `tag-release` pushed `vX.Y.Z` and nothing consumed it: the tag was
  decorative and every artifact-producing step was an unwritten manual
  ritual. Two entry points: a tag push runs the real release (security
  audit, build, PyPI upload, GitHub Release with wheels, sdist,
  `SHA256SUMS`, and a best-effort SBOM), and `workflow_dispatch` with
  `dry_run=true` runs the mandatory TestPyPI rehearsal.
- `tag-release --dry-run`, and recovery for an already-existing tag.
- Signing-key detection in `tag-release`: `$GPG_KEY_ID`, then
  `git config user.signingkey` (honoring `gpg.format`, so SSH signing keys
  work). With neither, the script explains the options and offers an
  unsigned annotated tag instead of dying on a raw `gpg` error.
- `tag-release` refuses to push when `.github/workflows/release.yml` is
  absent from `main` — the guard for the failure mode above.

### Changed

- **Release ordering inverted.** The tag no longer records an upload that
  already happened; it *causes* the upload. `AGENTS.md`, the release-workflow
  playbook, and the `prepare-release` handoff all reflect the new sequence:
  merge → rehearse on TestPyPI → tag (publishes).
- Index-token custody moved from "human's shell at upload time" to GitHub
  repository secrets (`PYPI_TOKEN`, `TEST_PYPI_TOKEN`), readable only by the
  release workflow. The agent still never holds, reads, or uses an index
  token. `AGENTS.md` §Security Boundaries and `ALLOWED_WEBSITES.md` amended
  to state the boundary in its new location.
- `.github/` is now covered by the SPDX header check (`scripts/license-headers`)
  and by yamllint in both the pre-commit hook and the Woodpecker gate. A new
  CI directory would otherwise have been exempt from both.
- `release-check` names its missing prerequisites (`build`, `twine`, which
  ship in the `[dev]` extra) instead of failing with a `ModuleNotFoundError`
  traceback.

### Fixed

- The release-workflow playbook no longer claims the release scripts are
  "not yet ported" — they were ported before this change, leaving the
  playbook describing a state that had not been true for several commits.

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
