# SPDX-License-Identifier: AGPL-3.0-or-later
"""Behavioral tests for library scanning and the demo fixture builder.

How they work: scanning tests build real adapter directories under
``tmp_path`` (reusing ``test_init``'s scaffolding helpers where a valid
adapter is needed) and assert on the returned entries — what is included,
what is skipped, and what a broken manifest reports. Demo tests treat
``build_demo_library`` as a product feature with claims to check: the
demo adapter must pass the real ``verify_dir``, the tampered adapter must
fail it (that failure IS the demo's point — verification catching
tampering), the written weights must be structurally valid safetensors
(8-byte little-endian header length + JSON header + data), and two builds
must be byte-identical so the demo is deterministic, not a lottery.
"""

from __future__ import annotations

import hashlib
import json
import struct

from exploradora import demo, library
from exploradora.core import manifest, scaffold, verify

TOKENIZER_SHA = hashlib.sha256(b"tok").hexdigest()


def write_valid_adapter(parent, dirname="alpha-adapter"):
    d = parent / dirname
    d.mkdir()
    (d / "adapter.safetensors").write_bytes(b"\x01weights\x02" * 32)
    scaffold.scaffold(
        d,
        name=None,
        version=None,
        base_model="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        a0_seed=1,
        rank=4,
        parameterization="lora",
        tokenizer_sha256=TOKENIZER_SHA,
        generator_class="unknown",
        training_data="unspecified",
        license="Apache-2.0",
        weights_filename=None,
    )
    return d


# ----------------------------------------------------------------- scanning


def test_scan_missing_or_empty_library_is_empty(tmp_path):
    assert library.scan_library(tmp_path / "absent") == ()
    assert library.scan_library(tmp_path) == ()


def test_scan_includes_only_manifest_bearing_directories(tmp_path):
    write_valid_adapter(tmp_path, "beta-adapter")
    (tmp_path / "not-an-adapter").mkdir()          # no manifest.json: skipped
    (tmp_path / "loose-file.txt").write_text("x")  # not a directory: skipped
    entries = library.scan_library(tmp_path)
    assert [e.path.name for e in entries] == ["beta-adapter"]


def test_scan_orders_entries_by_directory_name(tmp_path):
    write_valid_adapter(tmp_path, "zeta")
    write_valid_adapter(tmp_path, "alpha")
    assert [e.path.name for e in library.scan_library(tmp_path)] == ["alpha", "zeta"]


def test_scan_valid_entry_carries_manifest_and_weights_size(tmp_path):
    d = write_valid_adapter(tmp_path)
    entry = library.scan_library(tmp_path)[0]
    assert entry.load_error is None
    assert entry.manifest is not None and entry.manifest["name"] == "alpha-adapter"
    assert entry.weights_size == (d / "adapter.safetensors").stat().st_size


def test_scan_unparsable_manifest_reports_load_error(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    (d / "manifest.json").write_text("{not json", encoding="utf-8")
    entry = library.scan_library(tmp_path)[0]
    assert entry.manifest is None
    assert entry.load_error is not None
    assert entry.weights_size is None


def test_scan_schema_invalid_manifest_reports_error_count(tmp_path):
    d = write_valid_adapter(tmp_path)
    doc = manifest.loads((d / "manifest.json").read_bytes())
    doc["frame"]["parameterization"] = "qlora"
    (d / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    entry = library.scan_library(tmp_path)[0]
    assert entry.manifest is None
    assert "invalid" in entry.load_error and "parameterization" in entry.load_error


def test_scan_missing_weights_file_leaves_size_none_but_manifest_present(tmp_path):
    d = write_valid_adapter(tmp_path)
    (d / "adapter.safetensors").unlink()
    entry = library.scan_library(tmp_path)[0]
    assert entry.manifest is not None
    assert entry.weights_size is None


# ----------------------------------------------------------------- rendering helpers


def test_frame_summary_names_model_rank_and_parameterization(tmp_path):
    d = write_valid_adapter(tmp_path)
    doc = manifest.loads((d / "manifest.json").read_bytes())
    s = library.frame_summary(doc)
    assert "Qwen/Qwen2.5-Coder-1.5B-Instruct" in s and "r4" in s and "lora" in s


def test_format_size_covers_the_unit_ladder():
    assert library.format_size(None) == "—"
    assert library.format_size(512) == "512 B"
    assert library.format_size(2048) == "2.0 KB"
    assert library.format_size(5 * 1000 * 1000) == "5.0 MB"
    assert library.format_size(3 * 1000**3) == "3.0 GB"


# ----------------------------------------------------------------- the demo fixture


def test_demo_adapter_passes_real_verification(tmp_path):
    demo_dir, _tampered = demo.build_demo_library(tmp_path)
    sections = verify.verify_dir(demo_dir)
    assert verify.ok_to_exit_zero(sections)


def test_tampered_adapter_fails_weights_integrity_and_that_is_the_point(tmp_path):
    _demo, tampered = demo.build_demo_library(tmp_path)
    by_name = {s.name: s for s in verify.verify_dir(tampered)}
    assert by_name[verify.SECTION_MANIFEST].status == verify.STATUS_OK
    assert by_name[verify.SECTION_WEIGHTS].status == verify.STATUS_FAILED


def test_demo_manifests_say_plainly_they_are_not_trained_adapters(tmp_path):
    demo_dir, tampered = demo.build_demo_library(tmp_path)
    for d in (demo_dir, tampered):
        doc = manifest.loads((d / "manifest.json").read_bytes())
        assert "not a trained adapter" in doc["provenance"]["training_data"].lower()


def test_demo_weights_are_structurally_valid_safetensors(tmp_path):
    demo_dir, _ = demo.build_demo_library(tmp_path)
    blob = (demo_dir / "adapter.safetensors").read_bytes()
    (header_len,) = struct.unpack("<Q", blob[:8])
    header = json.loads(blob[8 : 8 + header_len])
    tensors = {k: v for k, v in header.items() if k != "__metadata__"}
    data_len = len(blob) - 8 - header_len
    for spec in tensors.values():
        start, end = spec["data_offsets"]
        assert 0 <= start <= end <= data_len
    assert max(spec["data_offsets"][1] for spec in tensors.values()) == data_len


def test_demo_build_is_deterministic_across_directories(tmp_path):
    a_demo, a_tampered = demo.build_demo_library(tmp_path / "a")
    b_demo, b_tampered = demo.build_demo_library(tmp_path / "b")
    for a, b in ((a_demo, b_demo), (a_tampered, b_tampered)):
        assert (a / "adapter.safetensors").read_bytes() == (b / "adapter.safetensors").read_bytes()
        assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()


def test_demo_build_is_idempotent_and_never_rewrites_existing_adapters(tmp_path):
    demo_dir, tampered = demo.build_demo_library(tmp_path)
    before = {
        p: p.read_bytes() for d in (demo_dir, tampered) for p in sorted(d.iterdir())
    }
    demo.build_demo_library(tmp_path)  # second run: a no-op, not a rebuild
    after = {
        p: p.read_bytes() for d in (demo_dir, tampered) for p in sorted(d.iterdir())
    }
    assert before == after
