<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## CI Debugging Protocol
When CI fails but tests pass locally, use `./scripts/ci-debug`:

```bash
# List recent CI runs (shows status, commit SHA)
./scripts/ci-debug runs

# Check status of current commit
./scripts/ci-debug status
```

(`ci-debug analyze-deps` also exists but its heuristics were tuned for
hypergumbo's tree-sitter dependency tree; treat its output as advisory here.)

**`auto-pr` exit-code recovery.** When `./scripts/auto-pr` exits non-zero:

- **Exit 0:** Success — PR merged or vPR queued. If vPR queued, run `./scripts/auto-pr flush` when remote is available.
- **Exit 1:** Failure. Run `./scripts/ci-debug status` to diagnose, fix the issue, then either re-run `./scripts/auto-pr` or `./scripts/merge-pr <PR_NUM> --wait-for-ci`.
- **Exit 2:** Timeout (CI stuck or slow). Try `./scripts/merge-pr <PR_NUM> --wait-for-ci --timeout 3600`, or if CI already passed, `./scripts/merge-pr <PR_NUM>` to merge immediately. If CI remains stuck, follow Scenario B.
- **Exit 3:** Hung (no CI jobs started after 5 min). `auto-pr` already retried with exponential backoff (close PR, wait, repush — up to 4 times). All retries failed, meaning CI runners may be down. Follow Scenario B. Do NOT manually kill processes, clear PR_PENDING, or start new branches.

**Scenario B (CI stuck after timeout).** Do NOT accumulate more changes to git-tracked exploradora code. Run `./scripts/ci-debug status` once per hour (manually, not in a loop). When CI recovers, use `./scripts/merge-pr <PR_NUM>` to merge. It is fine to wait.

**CI workflow topology (current):**
- **`.woodpecker/woodpecker.yml`**: The per-PR gate (lint, DCO, tests with 100% coverage, package build + fresh-venv wheel install + console-script smoke). Status context `ci/woodpecker/pr/woodpecker`. This is the ONLY workflow right now; full-suite/nightly matrices arrive post-v0.1 if the suite outgrows the per-PR gate.

**Common root causes**:
- **Missing dependencies**: code imports a package not listed in `pyproject.toml` (the fresh-venv wheel-install step exists to catch exactly this)
- **Missing package data**: the TUI fixture or schema file not included in the wheel (again: fresh-venv step)
- **Version mismatch**: CI has different package versions than local
- **Platform differences**: some packages don't have wheels for CI's platform

**The escape-hatch policy** (no `skipif` / `pytest.skip()` patterns):
- Tests assume dependencies work; they do **NOT** skip when dependencies fail. If a runtime dep breaks upstream, CI must fail loudly rather than silently green.
- Recovery procedure when an upstream dep breaks: pin to the last known-good version in `pyproject.toml`, add a comment naming the upstream issue or PR that motivated the pin, and ship the pin in its own PR so CI returns to green.
- Graceful-degradation behavior (an optional feature reporting itself unavailable) is tested via **mocking**, never by running the test suite with the dependency genuinely missing.
- Three escape-hatch shapes that must not appear in test files:
  - module-level `pytestmark = pytest.mark.skipif(not is_available(), ...)`
  - per-test `@pytest.mark.skipif(not AVAILABLE, ...)`
  - runtime `if result.skipped: pytest.skip(...)`
- Detail in the optional-dependency-testing playbook.
