# SPDX-License-Identifier: AGPL-3.0-or-later
"""Behavioral tests for the CLI entry point.

How they work: every test calls ``exploradora.cli.main()`` (or the parser
builder) in-process with an explicit argv, per the coverage playbook —
subprocess invocations would not count toward coverage and are reserved for
true integration tests (the CI package step smokes the installed console
script separately). Assertions are on observable behavior: exit codes, stdout
content, and argparse's documented exit conventions.
"""

from __future__ import annotations

import pytest

from exploradora import cli


def test_bare_invocation_prints_help_and_succeeds(capsys):
    """No subcommands exist, so `exploradora` explains itself and exits 0."""
    rc = cli.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage: exploradora" in out
    assert "pre-alpha" in out          # the honest status line is user-visible


def test_help_flag_exits_zero_and_names_the_status(capsys):
    """`--help` follows argparse convention: prints help, raises SystemExit(0)."""
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage: exploradora" in out
    assert "pre-alpha" in out


def test_version_flag_reports_the_installed_version(capsys):
    """`--version` prints the distribution version, not a hardcoded copy."""
    from importlib.metadata import version

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert version("exploradora") in capsys.readouterr().out


def test_unknown_argument_fails_with_argparse_conventions(capsys):
    """An unknown flag exits 2 (argparse's usage-error code) and says why."""
    with pytest.raises(SystemExit) as exc:
        cli.main(["--no-such-flag"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments" in err


def test_only_implemented_verbs_are_advertised(capsys):
    """Honesty guard: the parser's subcommands are exactly the implemented verbs.

    Unbuilt verbs (init/demo, the TUI) may appear only inside the roadmap-voice
    status sentence. This test is the place a new verb gets added — deliberately,
    with its feature — and fails on any drive-by registration.
    """
    parser = cli.build_parser()
    subactions = [a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"]
    assert len(subactions) == 1
    assert sorted(subactions[0].choices) == ["verify"]
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    assert "under construction" in capsys.readouterr().out
