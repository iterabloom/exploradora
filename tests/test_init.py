# SPDX-License-Identifier: AGPL-3.0-or-later
"""Behavioral tests for `exploradora init` — manifest scaffolding, core and CLI.

How they work: each test builds a real directory under ``tmp_path`` with
actual weights bytes (and, where relevant, a tokenizer file), runs the
scaffold through the core function or ``cli.main()`` in-process, and asserts
on what lands on disk: the manifest must validate, its hashes must match the
real file bytes, and ``verify_dir`` on the scaffolded directory must pass —
init's contract is "the manifest it writes is one verify accepts". Error
paths assert that NOTHING is written: a scaffold that fails halfway must not
leave a half-manifest behind.

Design decisions pinned here, per the honesty rules: authored facts
(base model, seed, rank, parameterization, tokenizer hash, license) are
required flags — init never guesses them; ``generator_class`` defaults to the
schema's explicit ``"unknown"``, never to a plausible value; claims and
attestations start EMPTY (no claim exists until something checked it).
"""

from __future__ import annotations

import hashlib

import pytest

from exploradora import cli
from exploradora.core import manifest, scaffold, verify

WEIGHTS = b"\x7fPRETEND-WEIGHTS\x00" * 128
TOKENIZER = b'{"pretend": "tokenizer"}'


def adapter_dir(tmp_path, weights_name="adapter.safetensors"):
    d = tmp_path / "demo-adapter"
    d.mkdir()
    (d / weights_name).write_bytes(WEIGHTS)
    return d


def base_options(d, **overrides):
    opts = dict(
        adapter_dir=d,
        name=None,
        version=None,
        base_model="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        a0_seed=42,
        rank=16,
        parameterization="lora",
        tokenizer_sha256=hashlib.sha256(TOKENIZER).hexdigest(),
        generator_class="unknown",
        training_data="unspecified",
        license="Apache-2.0",
        weights_filename=None,
    )
    opts.update(overrides)
    return opts


def cli_args(d, *extra):
    return [
        "init",
        str(d),
        "--base-model", "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "--a0-seed", "42",
        "--rank", "16",
        "--parameterization", "lora",
        "--tokenizer-sha256", hashlib.sha256(TOKENIZER).hexdigest(),
        "--license", "Apache-2.0",
        *extra,
    ]


# ----------------------------------------------------------------- core scaffold


def test_scaffold_writes_a_manifest_verify_accepts(tmp_path):
    d = adapter_dir(tmp_path)
    doc, ident = scaffold.scaffold(**base_options(d))
    on_disk = manifest.loads((d / "manifest.json").read_bytes())
    assert on_disk == doc
    assert manifest.validate(on_disk) == []
    assert ident == manifest.identity(on_disk)
    assert on_disk["weights"]["filename"] == "adapter.safetensors"
    assert on_disk["weights"]["sha256"] == hashlib.sha256(WEIGHTS).hexdigest()
    statuses = [s.status for s in verify.verify_dir(d)]
    assert statuses == [verify.STATUS_OK, verify.STATUS_OK, verify.STATUS_UNCHECKED]


def test_scaffold_defaults_are_the_honest_ones(tmp_path):
    d = adapter_dir(tmp_path)
    doc, _ = scaffold.scaffold(**base_options(d))
    assert doc["name"] == "demo-adapter"          # the directory's own name
    assert doc["version"] == "0.0.0"              # explicitly unreleased
    assert doc["provenance"]["generator_class"] == "unknown"
    assert doc["provenance"]["training_data"] == "unspecified"
    assert doc["claims"] == []                    # no claim until something checked it
    assert doc["attestations"] == []


def test_scaffold_explicit_name_and_version_win(tmp_path):
    d = adapter_dir(tmp_path)
    doc, _ = scaffold.scaffold(**base_options(d, name="my-adapter", version="1.2.3"))
    assert doc["name"] == "my-adapter"
    assert doc["version"] == "1.2.3"


def test_scaffold_manifest_file_is_pretty_json_with_trailing_newline(tmp_path):
    d = adapter_dir(tmp_path)
    scaffold.scaffold(**base_options(d))
    text = (d / "manifest.json").read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.count("\n") > 10  # indented, human-editable — not one JCS line


def test_scaffold_refuses_to_overwrite_an_existing_manifest(tmp_path):
    d = adapter_dir(tmp_path)
    (d / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(scaffold.ScaffoldError, match="already exists"):
        scaffold.scaffold(**base_options(d))
    assert (d / "manifest.json").read_text(encoding="utf-8") == "{}"  # untouched


def test_scaffold_requires_a_directory(tmp_path):
    with pytest.raises(scaffold.ScaffoldError, match="not a directory"):
        scaffold.scaffold(**base_options(tmp_path / "absent"))


def test_scaffold_error_when_no_weights_candidate(tmp_path):
    d = tmp_path / "empty-adapter"
    d.mkdir()
    with pytest.raises(scaffold.ScaffoldError, match="no weights file"):
        scaffold.scaffold(**base_options(d))
    assert not (d / "manifest.json").exists()


def test_scaffold_single_safetensors_wins_among_several_files(tmp_path):
    d = adapter_dir(tmp_path)
    (d / "notes.txt").write_bytes(b"training notes")
    doc, _ = scaffold.scaffold(**base_options(d))
    assert doc["weights"]["filename"] == "adapter.safetensors"


def test_scaffold_ambiguous_candidates_are_all_named_in_the_error(tmp_path):
    d = adapter_dir(tmp_path)
    (d / "other.safetensors").write_bytes(b"second candidate")
    with pytest.raises(scaffold.ScaffoldError, match="adapter.safetensors") as exc:
        scaffold.scaffold(**base_options(d))
    assert "other.safetensors" in str(exc.value)
    assert not (d / "manifest.json").exists()


def test_scaffold_hidden_files_are_not_candidates(tmp_path):
    d = adapter_dir(tmp_path)
    (d / ".DS_Store").write_bytes(b"noise")
    doc, _ = scaffold.scaffold(**base_options(d))
    assert doc["weights"]["filename"] == "adapter.safetensors"


def test_scaffold_explicit_weights_filename_wins(tmp_path):
    d = adapter_dir(tmp_path, weights_name="w1.safetensors")
    (d / "w2.safetensors").write_bytes(b"decoy")
    doc, _ = scaffold.scaffold(**base_options(d, weights_filename="w1.safetensors"))
    assert doc["weights"]["filename"] == "w1.safetensors"
    assert doc["weights"]["sha256"] == hashlib.sha256(WEIGHTS).hexdigest()


def test_scaffold_explicit_weights_must_exist(tmp_path):
    d = adapter_dir(tmp_path)
    with pytest.raises(scaffold.ScaffoldError, match="absent.safetensors"):
        scaffold.scaffold(**base_options(d, weights_filename="absent.safetensors"))


def test_scaffold_invalid_field_values_report_and_write_nothing(tmp_path):
    d = adapter_dir(tmp_path)
    with pytest.raises(scaffold.ScaffoldError, match=r"\$\.frame\.rank"):
        scaffold.scaffold(**base_options(d, rank=0))
    assert not (d / "manifest.json").exists()


def test_scaffold_bad_default_name_points_at_the_name_flag(tmp_path):
    d = tmp_path / "My Adapter"          # violates the name pattern
    d.mkdir()
    (d / "adapter.safetensors").write_bytes(WEIGHTS)
    with pytest.raises(scaffold.ScaffoldError, match=r"\$\.name"):
        scaffold.scaffold(**base_options(d))
    assert not (d / "manifest.json").exists()


# ----------------------------------------------------------------- CLI wiring


def test_cli_init_happy_path_prints_identity_and_next_step(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    rc = cli.main(cli_args(d))
    out = capsys.readouterr().out
    assert rc == 0
    doc = manifest.loads((d / "manifest.json").read_bytes())
    assert manifest.identity(doc) in out
    assert "verify" in out  # points the user at the next verb


def test_cli_init_tokenizer_file_is_hashed(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    tok = tmp_path / "tokenizer.json"
    tok.write_bytes(TOKENIZER)
    args = [a for a in cli_args(d) if a != "--tokenizer-sha256"]
    args.remove(hashlib.sha256(TOKENIZER).hexdigest())
    rc = cli.main([*args, "--tokenizer", str(tok)])
    assert rc == 0
    doc = manifest.loads((d / "manifest.json").read_bytes())
    assert doc["frame"]["tokenizer_sha256"] == hashlib.sha256(TOKENIZER).hexdigest()


def test_cli_init_tokenizer_flags_are_mutually_exclusive_and_one_is_required(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cli.main([*cli_args(d), "--tokenizer", "somewhere.json"])
    assert exc.value.code == 2
    args = [a for a in cli_args(d) if a != "--tokenizer-sha256"]
    args.remove(hashlib.sha256(TOKENIZER).hexdigest())
    with pytest.raises(SystemExit) as exc:
        cli.main(args)
    assert exc.value.code == 2


def test_cli_init_missing_tokenizer_file_is_a_clean_failure(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    args = [a for a in cli_args(d) if a != "--tokenizer-sha256"]
    args.remove(hashlib.sha256(TOKENIZER).hexdigest())
    rc = cli.main([*args, "--tokenizer", str(tmp_path / "absent.json")])
    assert rc == 1
    assert "absent.json" in capsys.readouterr().err
    assert not (d / "manifest.json").exists()


def test_cli_init_scaffold_errors_go_to_stderr_with_exit_one(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    (d / "manifest.json").write_text("{}", encoding="utf-8")
    rc = cli.main(cli_args(d))
    captured = capsys.readouterr()
    assert rc == 1
    assert "already exists" in captured.err


def test_cli_init_validation_errors_list_every_problem(tmp_path, capsys):
    d = adapter_dir(tmp_path)
    rc = cli.main([*cli_args(d, "--name", "BAD NAME", "--rank", "0")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "$.name" in captured.err and "$.frame.rank" in captured.err
    assert not (d / "manifest.json").exists()


def test_scaffolded_manifest_round_trips_byte_stable(tmp_path):
    """Preserve-plus-reserialize on the scaffold output is byte-stable (JCS discipline)."""
    from exploradora.core import jcs

    d = adapter_dir(tmp_path)
    doc, _ = scaffold.scaffold(**base_options(d))
    once = jcs.dumps(doc)
    assert jcs.dumps(jcs.loads(once)) == once
