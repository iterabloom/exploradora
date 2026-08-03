<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## Pre-Work Playbook
Run these checks before starting any new feature or task:
```bash
# 1. Ensure no auto-pr is in flight (manual PRs don't create this file)
test -f .git/PR_PENDING && echo "STOP: auto-pr awaiting merge" && exit 1

# 2. Flush any queued vPRs if remote is available
./scripts/auto-pr list  # Check if any PRs are queued
./scripts/auto-pr flush # Push them if remote is back

# 3. Sync with dev from origin (the only remote)
git fetch origin dev
git checkout dev && git merge --ff-only origin/dev

# 4. Check current progress (at your careful discretion, use `head`,
#    `tail`, `sed`, `grep`, etc, for efficient reading)
cat README.md        # STATUS section is kept accurate
cat CHANGELOG.md     # once it exists (lands with the package skeleton)

# 5. Create feature branch
git checkout -b <author>/feat/<short-name>
```
