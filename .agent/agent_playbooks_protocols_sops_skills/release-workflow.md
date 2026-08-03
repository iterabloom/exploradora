<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## Release Workflow (Agent + Human)

Releases use a two-step workflow that separates agent preparation from human
authorization. **Script status (honest gap):** `prepare-release`,
`release-check`, `bump-version`, and `tag-release` are not yet ported from
hypergumbo — they land, adapted, with the v0.1 release preparation. This
playbook is the contract they will implement.

### Agent Preparation
```bash
# Agent runs this to prepare everything
./scripts/prepare-release 0.1.0

# This script:
# 1. Bumps version in pyproject.toml
# 2. Updates CHANGELOG.md ([Unreleased] → [0.1.0])
# 3. Commits: "chore: release 0.1.0"
# 4. Runs ./scripts/release-check — which must include:
#      python -m build; twine check dist/*;
#      fresh-venv wheel install + test suite + console-script smoke
# 5. Creates PR: dev → main
# 6. Outputs handoff instructions, then STOPS.
```

The agent never uploads to a package index. PyPI/TestPyPI tokens are
human-held (AGENTS.md §Security Boundaries).

### Human Actions (Required)
```bash
# 1. Review and merge the dev → main PR on GitHub

# 2. Rehearse the full upload → install-from-index loop on TestPyPI:
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --no-deps exploradora  # in a fresh venv
#    The rehearsal is not skippable, including under time pressure.

# 3. Real upload:
twine upload dist/*

# 4. Tag the release (GPG-signed), AFTER the upload succeeded:
./scripts/tag-release 0.1.0
```

### Why Two Steps?
- **Branch protection:** main cannot be pushed to directly
- **Credential isolation:** index tokens never touch the agent
- **GPG signing:** the tag is signed with the human's key
- **Authorization:** the human explicitly approves the release

### Scripts Reference
| Script | Who | Purpose | Status |
|--------|-----|---------|--------|
| `./scripts/prepare-release VERSION` | Agent | Prepare everything, create PR | not yet ported |
| `./scripts/tag-release VERSION` | Human | Sign and push tag after upload | not yet ported |
| `./scripts/release-check` | Either | Validate release readiness | not yet ported |
| `./scripts/bump-version VERSION` | Either | Just bump version | not yet ported |
