<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
## Testing Optional Dependencies

When code depends on a package that may be absent at runtime (an optional
extra, a heavyweight dep deliberately not required):

**DO NOT use pytest.mark.skipif escape hatches.** Write real tests that:
1. Directly call the code with the dependency installed (CI installs it)
2. Assert on real results
3. Use mocking ONLY for testing the "unavailable" code path

```python
# Real test — uses the actually-installed dependency
def test_feature_works(self, tmp_path: Path) -> None:
    result = do_thing(tmp_path)
    assert not result.skipped
    assert result.value == expected

# Mock test — only for testing unavailability handling
def test_skipped_when_unavailable(self, tmp_path: Path) -> None:
    with patch.object(module, "is_dep_available", return_value=False):
        with pytest.warns(UserWarning, match="skipped"):
            result = module.do_thing(tmp_path)
    assert result.skipped is True
```

Three escape-hatch shapes that must not appear in test files:
- module-level `pytestmark = pytest.mark.skipif(not is_available(), ...)`
- per-test `@pytest.mark.skipif(not AVAILABLE, ...)`
- runtime `if result.skipped: pytest.skip(...)`

Why: a skipped test is a silently-green test. If the dependency breaks
upstream, CI must fail loudly; the recovery is a pinned known-good version in
`pyproject.toml` with a comment naming the upstream issue, shipped in its own
PR (see the ci-debug protocol's escape-hatch policy).
