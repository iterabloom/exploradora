# SPDX-License-Identifier: AGPL-3.0-or-later
"""Behavioral tests for the TUI and its CLI wiring.

How they work: the app itself runs headless under Textual's test pilot
(``App.run_test``), driven from synchronous tests via ``asyncio.run`` so no
async pytest plugin is needed. Assertions are on what a user would see:
table rows, the detail pane's text, and the status column moving from
``unchecked`` to a real verification verdict when ``v`` is pressed — on the
demo library, so the fixture the product ships is the fixture the tests
exercise. CLI dispatch tests monkeypatch only ``tui.run_browser`` (the
blocking terminal loop — everything up to the launch runs real), asserting
which library path each verb hands it.
"""

from __future__ import annotations

import asyncio

from exploradora import cli, demo, library, tui
from exploradora.core import verify

OK_SUMMARY = "integrity-ok · claims unchecked"


def sections(*statuses):
    names = (verify.SECTION_MANIFEST, verify.SECTION_WEIGHTS, verify.SECTION_CLAIMS)
    return tuple(
        verify.Section(n, s, ("detail",)) for n, s in zip(names, statuses, strict=True)
    )


# ----------------------------------------------------------------- status_summary


def test_status_summary_never_says_green_while_anything_is_unchecked():
    got = tui.status_summary(
        sections(verify.STATUS_OK, verify.STATUS_OK, verify.STATUS_UNCHECKED)
    )
    assert got == OK_SUMMARY


def test_status_summary_any_failure_reads_failed():
    got = tui.status_summary(
        sections(verify.STATUS_OK, verify.STATUS_FAILED, verify.STATUS_UNCHECKED)
    )
    assert got == "integrity-failed"


def test_status_summary_nothing_checked_stays_unchecked():
    got = tui.status_summary(
        sections(verify.STATUS_UNCHECKED, verify.STATUS_UNCHECKED, verify.STATUS_UNCHECKED)
    )
    assert got == "unchecked"


def test_status_summary_all_checked_and_passing_is_plain_ok():
    got = tui.status_summary(sections(verify.STATUS_OK, verify.STATUS_OK, verify.STATUS_OK))
    assert got == "integrity-ok"


# ----------------------------------------------------------------- the app, piloted


def drive(coro):
    return asyncio.run(coro)


def test_browser_lists_demo_adapters_with_unchecked_status(tmp_path):
    demo.build_demo_library(tmp_path)

    async def scenario():
        app = tui.AdapterBrowser(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one("DataTable")
            assert table.row_count == 2
            row0 = [str(c) for c in table.get_row_at(0)]
            assert "demo-adapter" in row0[0]
            assert "unchecked" in row0[-1]
            detail = app.query_one("#detail").content
            assert "demo-adapter" in str(detail)

    drive(scenario())


def test_pressing_v_verifies_the_selected_row_and_updates_status(tmp_path):
    demo.build_demo_library(tmp_path)

    async def scenario():
        app = tui.AdapterBrowser(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("v")
            await pilot.pause()
            table = app.query_one("DataTable")
            assert OK_SUMMARY in [str(c) for c in table.get_row_at(0)]
            assert "claim replay is not implemented" in str(app.query_one("#detail").content)

    drive(scenario())


def test_tampered_row_verifies_as_failed(tmp_path):
    demo.build_demo_library(tmp_path)

    async def scenario():
        app = tui.AdapterBrowser(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down")   # move to tampered-adapter (row 2 of 2)
            await pilot.pause()
            detail_before = str(app.query_one("#detail").content)
            assert "tampered-adapter" in detail_before
            await pilot.press("v")
            await pilot.pause()
            table = app.query_one("DataTable")
            assert "integrity-failed" in [str(c) for c in table.get_row_at(1)]
            assert "sha256 mismatch" in str(app.query_one("#detail").content)

    drive(scenario())


def test_broken_manifest_row_shows_its_load_error_in_the_detail_pane(tmp_path):
    demo.build_demo_library(tmp_path)
    broken = tmp_path / "aa-broken"          # sorts first
    broken.mkdir()
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")

    async def scenario():
        app = tui.AdapterBrowser(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one("DataTable")
            assert table.row_count == 3
            assert "aa-broken" in [str(c) for c in table.get_row_at(0)]
            assert "manifest could not be loaded" in str(app.query_one("#detail").content)
            await pilot.press("v")           # verify still runs; it reports the failure
            await pilot.pause()
            assert "integrity-failed" in [str(c) for c in table.get_row_at(0)]

    drive(scenario())


def test_empty_library_shows_a_hint_and_v_is_harmless(tmp_path):
    async def scenario():
        app = tui.AdapterBrowser(tmp_path / "absent")
        async with app.run_test() as pilot:
            await pilot.pause()
            hint = str(app.query_one("#empty").content)
            assert "no adapters" in hint
            assert "exploradora demo" in hint
            await pilot.press("v")           # nothing selected: must not crash
            await pilot.pause()

    drive(scenario())


def test_q_quits(tmp_path):
    demo.build_demo_library(tmp_path)

    async def scenario():
        app = tui.AdapterBrowser(tmp_path)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
        assert app._exit  # the binding ended the app, not the context manager

    drive(scenario())


# ----------------------------------------------------------------- CLI dispatch


def test_cli_browse_launches_on_the_given_path(tmp_path, monkeypatch):
    launched = []
    monkeypatch.setattr(tui, "run_browser", launched.append)
    rc = cli.main(["browse", str(tmp_path)])
    assert rc == 0
    assert launched == [tmp_path]


def test_cli_browse_defaults_to_the_home_library(monkeypatch):
    launched = []
    monkeypatch.setattr(tui, "run_browser", launched.append)
    assert cli.main(["browse"]) == 0
    assert launched == [library.DEFAULT_LIBRARY_DIR]


def test_cli_bare_invocation_opens_the_browser_on_the_default_library(monkeypatch):
    launched = []
    monkeypatch.setattr(tui, "run_browser", launched.append)
    assert cli.main([]) == 0
    assert launched == [library.DEFAULT_LIBRARY_DIR]


def test_cli_demo_builds_the_fixture_then_browses_it(tmp_path, monkeypatch):
    launched = []
    monkeypatch.setattr(tui, "run_browser", launched.append)
    target = tmp_path / "demolib"
    rc = cli.main(["demo", "--library", str(target)])
    assert rc == 0
    assert launched == [target]
    assert verify.ok_to_exit_zero(verify.verify_dir(target / demo.DEMO_ADAPTER))


def test_cli_demo_defaults_to_the_home_demo_dir(monkeypatch, tmp_path):
    launched = []
    monkeypatch.setattr(tui, "run_browser", launched.append)
    built = []
    monkeypatch.setattr(demo, "build_demo_library", lambda p: built.append(p))
    assert cli.main(["demo"]) == 0
    assert built == [demo.DEFAULT_DEMO_DIR] and launched == [demo.DEFAULT_DEMO_DIR]
