# SPDX-License-Identifier: AGPL-3.0-or-later
"""Behavioral tests for adapter-directory verification, core and CLI.

How they work: each test builds a real adapter directory under ``tmp_path`` —
actual weights bytes, actual ``manifest.json`` — mutates exactly one thing,
and asserts on the returned sections: their statuses, their order, and the
evidence strings a user would read. The CLI tests call ``cli.main()``
in-process (subprocess runs would not count toward coverage) and assert the
rendered table plus the exit-code contract. ``make_manifest`` is shared with
the schema tests so "valid" means the same thing everywhere.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from test_manifest import make_manifest

from exploradora import cli
from exploradora.core import verify
from exploradora.core.verify import (
    SECTION_CLAIMS,
    SECTION_MANIFEST,
    SECTION_WEIGHTS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_UNCHECKED,
)

WEIGHTS = b"\x00pretend-safetensors-bytes\x01" * 64


def write_adapter(tmp_path, manifest_doc=None, weights=WEIGHTS):
    """A real adapter dir: weights bytes + manifest.json whose hash matches them."""
    if manifest_doc is None:
        manifest_doc = make_manifest()
        manifest_doc["weights"]["sha256"] = hashlib.sha256(weights).hexdigest()
    (tmp_path / manifest_doc["weights"]["filename"]).write_bytes(weights)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest_doc), encoding="utf-8")
    return tmp_path


def by_name(sections):
    return {s.name: s for s in sections}


# ----------------------------------------------------------------- core sections


def test_valid_adapter_checks_pass_and_claims_stay_unchecked(tmp_path):
    sections = verify.verify_dir(write_adapter(tmp_path))
    assert [s.name for s in sections] == [SECTION_MANIFEST, SECTION_WEIGHTS, SECTION_CLAIMS]
    got = by_name(sections)
    assert got[SECTION_MANIFEST].status == STATUS_OK
    assert "identity" in got[SECTION_MANIFEST].details[0]
    assert got[SECTION_WEIGHTS].status == STATUS_OK
    assert got[SECTION_CLAIMS].status == STATUS_UNCHECKED
    assert "NOT checked" in got[SECTION_CLAIMS].details[0]
    assert verify.ok_to_exit_zero(sections)


def test_missing_manifest_fails_schema_and_leaves_weights_unchecked(tmp_path):
    sections = verify.verify_dir(tmp_path)
    got = by_name(sections)
    assert got[SECTION_MANIFEST].status == STATUS_FAILED
    assert "not found" in got[SECTION_MANIFEST].details[0]
    assert got[SECTION_WEIGHTS].status == STATUS_UNCHECKED
    assert not verify.ok_to_exit_zero(sections)


def test_unparsable_manifest_reports_the_parse_error(tmp_path):
    (tmp_path / "manifest.json").write_text('{"a": 1, "a": 2}', encoding="utf-8")
    got = by_name(verify.verify_dir(tmp_path))
    assert got[SECTION_MANIFEST].status == STATUS_FAILED
    assert "duplicate" in got[SECTION_MANIFEST].details[0]
    assert got[SECTION_WEIGHTS].status == STATUS_UNCHECKED


def test_non_object_manifest_reports_the_shape_error(tmp_path):
    (tmp_path / "manifest.json").write_text("[1, 2]", encoding="utf-8")
    got = by_name(verify.verify_dir(tmp_path))
    assert got[SECTION_MANIFEST].status == STATUS_FAILED
    assert "JSON object" in got[SECTION_MANIFEST].details[0]


def test_schema_invalid_manifest_lists_errors_and_skips_weights(tmp_path):
    doc = make_manifest()
    doc["frame"]["parameterization"] = "qlora"
    write_adapter(tmp_path, manifest_doc=doc)
    got = by_name(verify.verify_dir(tmp_path))
    assert got[SECTION_MANIFEST].status == STATUS_FAILED
    assert any("parameterization" in d for d in got[SECTION_MANIFEST].details)
    assert got[SECTION_WEIGHTS].status == STATUS_UNCHECKED
    assert "manifest invalid" in got[SECTION_WEIGHTS].details[0]


def test_missing_weights_file_fails_that_section_alone(tmp_path):
    write_adapter(tmp_path)
    (tmp_path / make_manifest()["weights"]["filename"]).unlink()
    got = by_name(verify.verify_dir(tmp_path))
    assert got[SECTION_MANIFEST].status == STATUS_OK
    assert got[SECTION_WEIGHTS].status == STATUS_FAILED
    assert "not found" in got[SECTION_WEIGHTS].details[0]


def test_hash_mismatch_shows_both_hashes(tmp_path):
    write_adapter(tmp_path)
    fname = make_manifest()["weights"]["filename"]
    (tmp_path / fname).write_bytes(b"tampered")
    got = by_name(verify.verify_dir(tmp_path))
    assert got[SECTION_WEIGHTS].status == STATUS_FAILED
    joined = " ".join(got[SECTION_WEIGHTS].details)
    assert "manifest says" in joined and "file bytes hash to" in joined
    assert hashlib.sha256(b"tampered").hexdigest() in joined


def test_the_vocabulary_never_says_bare_verified(tmp_path):
    """The honesty rule as a test: statuses come from the three-word vocabulary only."""
    for sections in (verify.verify_dir(write_adapter(tmp_path)), verify.verify_dir(tmp_path)):
        for s in sections:
            assert s.status in (STATUS_OK, STATUS_FAILED, STATUS_UNCHECKED)
            assert s.status != "verified"


def test_nothing_ran_is_not_success():
    """ok_to_exit_zero: 'no failures because no checks' must read as failure."""
    all_unchecked = (
        verify.Section(SECTION_MANIFEST, STATUS_UNCHECKED, ("why",)),
        verify.Section(SECTION_WEIGHTS, STATUS_UNCHECKED, ("why",)),
        verify.Section(SECTION_CLAIMS, STATUS_UNCHECKED, ("why",)),
    )
    assert not verify.ok_to_exit_zero(all_unchecked)


def test_sha256_file_streams_large_input(tmp_path):
    blob = b"x" * (3 * (1 << 20) + 17)  # crosses several chunk boundaries
    p = tmp_path / "big.bin"
    p.write_bytes(blob)
    assert verify.sha256_file(p) == hashlib.sha256(blob).hexdigest()


# ----------------------------------------------------------------- CLI wiring


def test_cli_verify_happy_path_exits_zero_and_shows_every_section(tmp_path, capsys):
    rc = cli.main(["verify", str(write_adapter(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    for name in (SECTION_MANIFEST, SECTION_WEIGHTS, SECTION_CLAIMS):
        assert name in out
    assert STATUS_UNCHECKED in out          # claims visibly not checked
    assert "PASS" not in out                # no overall verdict line, no bare green


def test_cli_verify_failure_exits_one_and_names_the_failure(tmp_path, capsys):
    rc = cli.main(["verify", str(tmp_path)])  # empty dir: no manifest
    out = capsys.readouterr().out
    assert rc == 1
    assert STATUS_FAILED in out and "not found" in out


def test_cli_help_names_verify_and_only_verify_as_a_subcommand(capsys):
    parser = cli.build_parser()
    subactions = [a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction"]
    assert len(subactions) == 1
    assert sorted(subactions[0].choices) == ["verify"]  # implemented verbs only
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    assert "under construction" in capsys.readouterr().out
