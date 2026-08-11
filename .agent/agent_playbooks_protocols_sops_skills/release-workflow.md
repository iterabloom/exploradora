<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## Release Workflow (Agent + Human + CI)

Releases separate agent preparation from human authorization from machine
execution. The agent prepares and stops; a human reviews, rehearses, and
authorizes; CI performs the upload.

**Status (honest):** the scripts and the workflow exist. What has *not*
happened yet is an end-to-end run — no tag has ever been pushed in this
repository, so the release workflow has never executed. Treat the first real
release as a live test of this document, not a routine application of it.
Section "Unverified prerequisites" lists what has to be true and has not
been confirmed.

### Ordering (read this first)

The sequence inverted when publishing was automated. It used to be:
upload by hand, then tag to record what you uploaded. It is now:

> **the tag push is what publishes.**

The tag is the authorization signal. Once pushed, CI uploads to PyPI, and
**PyPI forbids reusing a version number** — there is no retry under the same
version. That is why the TestPyPI rehearsal is mandatory and why
`tag-release` prompts before pushing.

### Step 1 — Agent

```bash
./scripts/prepare-release 0.1.0
```

Bumps `pyproject.toml`, rolls `CHANGELOG.md` (`[Unreleased]` → `[0.1.0]`),
commits `chore: release 0.1.0`, runs `release-check`, merges the release
commit to `dev` via `auto-pr`, opens the `dev → main` PR with `--gov` (CI
runs, no auto-merge), prints the handoff, and **stops**.

`release-check` requires `build` and `twine`, which ship in the `[dev]`
extra rather than with the interpreter. On a machine with no dev install it
now fails with a named prerequisite instead of a `ModuleNotFoundError`
traceback:

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
```

### Step 2 — Human: merge

Review and merge the `dev → main` PR on GitHub. Checklist: version bumped,
CHANGELOG rolled, CI green.

### Step 3 — Human: rehearse on TestPyPI (not skippable)

GitHub → Actions → **Release** → *Run workflow*, leaving `dry_run=true`
(the default). This builds, runs the security audit, and uploads to
TestPyPI. It does **not** touch PyPI and does **not** cut a Release.

Then verify the artifact installs *from the index* — not from your checkout:

```bash
python3 -m venv /tmp/rehearse
/tmp/rehearse/bin/pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    exploradora==0.1.0
/tmp/rehearse/bin/exploradora --version
```

The `--extra-index-url` is load-bearing: TestPyPI is not a mirror of PyPI,
so runtime dependencies (here, `textual`) are not reliably resolvable there.
Without it, a plain `--index-url` install can fail on a *dependency* and be
misread as a failure of the exploradora artifact. If you want to test the
artifact alone and skip dependency resolution entirely, use `--no-deps` —
but then `exploradora --version` is the only smoke available, since the TUI
cannot import without `textual`.

The rehearsal is not skippable, including under time pressure.

### Step 4 — Human: tag (this publishes)

```bash
./scripts/tag-release 0.1.0            # add --dry-run to see the plan first
```

The script refuses to proceed unless: you are on `main`, in sync with
`origin/main`, the tree is clean, `pyproject.toml` matches the version,
and `.github/workflows/release.yml` exists on `main`. It prompts before
the push, because the push is irreversible.

**Signing.** Key detection order: `$GPG_KEY_ID`, then
`git config user.signingkey` (which honors `gpg.format`, so an SSH signing
key configured that way works too). With neither, the script explains the
options and offers an unsigned annotated tag rather than dying on a raw
`gpg` error. An unsigned release tag is acceptable for a rehearsal and not
for a release anyone is expected to trust.

### What CI does with the tag

`.github/workflows/release.yml`:

1. **security-audit** (hard gate) — `pip-audit` with no ignore list, `bandit`,
   informational dependency-license report.
2. **build-and-publish** — verifies the tag version matches `pyproject.toml`,
   builds sdist+wheel, `twine check`, installs the wheel into a fresh venv and
   runs the suite plus a `--version` smoke against it, generates `SHA256SUMS`
   and a best-effort SBOM, uploads to PyPI, and cuts the GitHub Release with
   assets and CHANGELOG-derived notes.

A missing `PYPI_TOKEN` on a tag push is a **hard failure**, not a warning: a
green release run that published nothing is exactly the unearned green light
this project's honesty rules forbid.

### Why the split

- **Branch protection:** `main` cannot be pushed to directly.
- **Credential isolation:** index tokens live in repository secrets, readable
  only by the workflow at run time — never by the agent, never in `.env`.
- **Signing:** the tag is signed with the human's key.
- **Authorization:** two distinct human acts (merge, then tag) gate the upload.

### Unverified prerequisites

None of the following has been confirmed on this repository. Check each
before the first release:

- **GitHub Actions is enabled.** This repository's per-PR CI is Woodpecker;
  the release workflow is its first use of Actions. If Actions is disabled
  for the repo or the org, the tag push will silently do nothing — the exact
  failure this workflow was written to eliminate.
- **`PYPI_TOKEN` and `TEST_PYPI_TOKEN` exist** in repository secrets, scoped
  to the `exploradora` project.
- **The PyPI project name `exploradora` is available** (or already owned).
  First upload claims it; if it is taken, the release fails at upload with
  the version already built and tagged.
- **`contents: write` is permitted** for `GITHUB_TOKEN` (org policy can
  restrict default workflow permissions, which would break `gh release create`).
- **A signing key exists** on the machine running `tag-release`.

### Scripts reference

| Script | Who | Purpose |
|--------|-----|---------|
| `./scripts/prepare-release VERSION` | Agent | Bump, roll changelog, check, open the dev→main PR, stop |
| `./scripts/release-check` | Either | Build, `twine check`, fresh-venv wheel install + suite + console-script smoke |
| `./scripts/bump-version VERSION` | Either | Just bump `pyproject.toml` |
| `./scripts/tag-release VERSION` | Human | Sign and push the tag — **this publishes** |
