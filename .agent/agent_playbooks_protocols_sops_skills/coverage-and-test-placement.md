<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
- **100% Coverage:** No code may be committed without full test coverage. Verify with:
  - **Fast (parallel):** `pytest -n auto --cov --cov-fail-under=100`
  - **Debug (sequential):** `pytest --cov --cov-fail-under=100`
  - Coverage paths are configured in `pyproject.toml`.
  - **No excuses:** If coverage drops below 100%, it is YOUR responsibility to fix it—even if you didn't cause it. "Not my fault" is not an acceptable response. Any coverage gap you encounter is technical debt that must be addressed before proceeding. Investigate the cause, fix it, and move on. This prevents debt accumulation.
  - Mark genuinely defensive paths with `# pragma: no cover` — sparingly, and only for code that cannot be reached by a production input.
- **Test Placement:** All tests live in `tests/` at the repo root (single-package layout). Tests for `exploradora.core` must not import from the AGPL client package — the core layer's no-client-imports rule (see `src/exploradora/core/__init__.py`) applies to its tests' *subjects*; testing core through client wrappers masks layer violations.
  - **Subprocess tests don't contribute to coverage:** Tests that invoke `subprocess.run([sys.executable, "-m", "exploradora", ...])` won't contribute to pytest-cov coverage. Call functions directly when possible. Use subprocess tests only for true integration testing (verifying CLI args, exit codes, etc.), not for coverage.
  - **TUI tests:** use Textual's pilot/runner for TUI coverage; snapshot tests supplement, never replace, behavioral assertions.
