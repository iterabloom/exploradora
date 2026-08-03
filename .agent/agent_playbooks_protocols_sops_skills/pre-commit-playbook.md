<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## Pre-Commit Playbook
Run these checks before every commit:
```bash
# 1. Verify git identity is configured
git config user.name && git config user.email

# 2. Run tests with coverage (must be 100%)
pytest -n auto --cov --cov-fail-under=100

# 3. If feature status changed: update CHANGELOG.md and, if the change is
#    user-visible, the README STATUS section (keep it accurate — Honesty
#    Rules in AGENTS.md).

# 4. Commit with sign-off
git commit -s -m "feat: description"
```
