# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for manifest validation, identity, and validator↔JSON-Schema lockstep.

How they work: a builder produces a fully valid manifest; every error branch
in the validator is then exercised by one targeted mutation with the expected
"path: problem" fragment asserted, so a regression names the exact field it
broke. Identity properties (order independence, unknown-field participation)
run under Hypothesis. The sync tests read the packaged ``manifest.schema.json``
through ``importlib.resources`` — which is also what proves the wheel ships
it — and compare its required lists, enums, patterns, and bounds against the
validator's constants, so the interop artifact cannot drift from the
executable truth. If ``jsonschema`` happens to be installed, the same
valid/invalid corpus is additionally judged by it (real dependency when
present, skip when absent — never a mock).
"""

from __future__ import annotations

import copy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from exploradora.core import jcs, manifest

HEX = "ab" * 32


def make_manifest() -> dict:
    """A fully valid schema_version-0 manifest; tests mutate copies of it."""
    return {
        "schema_version": 0,
        "name": "demo-adapter",
        "version": "0.1.0",
        "frame": {
            "base_model": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
            "a0_seed": 42,
            "rank": 16,
            "tokenizer_sha256": HEX,
            "parameterization": "lora",
        },
        "weights": {"filename": "adapter.safetensors", "sha256": HEX},
        "provenance": {
            "generator_class": "local",
            "training_data": "synthetic operator corpus, 32 examples",
            "license": "Apache-2.0",
        },
        "claims": [
            {
                "task_id": "toposort-cycle-detection",
                "result": "pass",
                "io_sha256": HEX,
                "recipe_note": "greedy decode, temperature 0, seeded harness v1",
                "verification": {
                    "mutation": {"killed": 38, "total": 40},
                    "property_coverage": {"covered": 3, "total": 3},
                    "spec_gap": {"found": 0, "probed": 12},
                    "spec_provenance": "upstream-suite",
                },
                "oracle_basis": "executable-oracle",
            }
        ],
        "attestations": [
            {
                "attester": "node-7f3a",
                "claim_ref": "toposort-cycle-detection",
                "agreement_relation": "verdict-level",
                "result": "agree",
            }
        ],
    }


def mutated(path_mutator) -> dict:
    m = make_manifest()
    path_mutator(m)
    return m


# ----------------------------------------------------------------- the happy path


def test_the_builder_manifest_is_valid_and_has_an_identity():
    m = make_manifest()
    assert manifest.validate(m) == []
    ident = manifest.identity(m)
    assert len(ident) == 64 and int(ident, 16) >= 0


def test_unknown_fields_are_legal_and_participate_in_identity():
    m = make_manifest()
    base = manifest.identity(m)
    m["x_future_field"] = {"anything": [1, "two", None]}
    m["claims"][0]["x_note"] = "extra"
    assert manifest.validate(m) == []
    assert manifest.identity(m) != base   # content, not decoration


def test_counter_pair_zero_denominator_means_unmeasured_and_is_valid():
    m = mutated(lambda m: m["claims"][0]["verification"].update(
        {"mutation": {"killed": 0, "total": 0}}))
    assert manifest.validate(m) == []


# ----------------------------------------------------------------- every error branch

_CASES = [
    ("not-an-object", lambda m: None, "$: expected object"),
    ("reserved-identity", lambda m: m.update({"identity": "x"}), "reserved"),
    ("not-canonicalizable", lambda m: m.update({"x": 1.5}), "not canonicalizable"),
    ("version-missing", lambda m: m.pop("schema_version"), "schema_version: required"),
    ("name-missing", lambda m: m.pop("name"), "$.name: required field missing"),
    ("license-missing", lambda m: m["provenance"].pop("license"), "license: required"),
    ("task-id-missing", lambda m: m["claims"][0].pop("task_id"), "task_id: required"),
    ("mutation-pair-missing", lambda m: m["claims"][0]["verification"].pop("mutation"),
     "mutation: required"),
    ("version-wrong", lambda m: m.update({"schema_version": 1}), "not the supported version"),
    ("version-bool", lambda m: m.update({"schema_version": True}), "expected integer, got bool"),
    ("name-pattern", lambda m: m.update({"name": "Bad Name!"}), "$.name: must match"),
    ("name-type", lambda m: m.update({"name": 7}), "$.name: expected string, got int"),
    ("semver-pattern", lambda m: m.update({"version": "+bad"}), "$.version: must match"),
    ("frame-not-object", lambda m: m.update({"frame": []}), "$.frame: expected object"),
    ("base-model-empty", lambda m: m["frame"].update({"base_model": ""}), "length outside"),
    ("a0-seed-negative", lambda m: m["frame"].update({"a0_seed": -1}), "outside"),
    ("rank-zero", lambda m: m["frame"].update({"rank": 0}), "outside [1, 65536]"),
    ("tokenizer-hex", lambda m: m["frame"].update({"tokenizer_sha256": "AB" * 32}),
     "not 64 lowercase hex"),
    ("parameterization", lambda m: m["frame"].update({"parameterization": "qlora"}),
     "not one of"),
    ("weights-filename-sep", lambda m: m["weights"].update({"filename": "a/b"}),
     "single path segment"),
    ("weights-filename-dots", lambda m: m["weights"].update({"filename": ".."}),
     "single path segment"),
    ("weights-hex", lambda m: m["weights"].update({"sha256": "zz" * 32}),
     "not 64 lowercase hex"),
    ("provenance-not-object", lambda m: m.update({"provenance": 3}),
     "$.provenance: expected object"),
    ("generator-class", lambda m: m["provenance"].update({"generator_class": "agi"}),
     "not one of"),
    ("license-empty", lambda m: m["provenance"].update({"license": ""}), "must not be empty"),
    ("claims-not-array", lambda m: m.update({"claims": "no"}), "$.claims: required"),
    ("claim-not-object", lambda m: m["claims"].append(3), "$.claims[1]: expected object"),
    ("task-id-empty", lambda m: m["claims"][0].update({"task_id": ""}), "must not be empty"),
    ("task-id-duplicate", lambda m: m["claims"].append(copy.deepcopy(m["claims"][0])),
     "duplicate"),
    ("claim-result", lambda m: m["claims"][0].update({"result": "maybe"}), "not one of"),
    ("io-hex", lambda m: m["claims"][0].update({"io_sha256": "g" * 64}),
     "not 64 lowercase hex"),
    ("verification-missing", lambda m: m["claims"][0].pop("verification"),
     "verification: required"),
    ("mutation-pair-inverted", lambda m: m["claims"][0]["verification"].update(
        {"mutation": {"killed": 5, "total": 4}}), "killed 5 exceeds total 4"),
    ("spec-gap-inverted", lambda m: m["claims"][0]["verification"].update(
        {"spec_gap": {"found": 2, "probed": 1}}), "found 2 exceeds probed 1"),
    ("coverage-pair-type", lambda m: m["claims"][0]["verification"].update(
        {"property_coverage": {"covered": "3", "total": 3}}), "expected integer, got str"),
    ("spec-provenance", lambda m: m["claims"][0]["verification"].update(
        {"spec_provenance": "vibes"}), "not one of"),
    ("oracle-basis", lambda m: m["claims"][0].update({"oracle_basis": "trust-me"}),
     "not one of"),
    ("attestations-not-array", lambda m: m.update({"attestations": {}}),
     "$.attestations: required"),
    ("attestation-not-object", lambda m: m["attestations"].append("x"),
     "$.attestations[1]: expected object"),
    ("attester-empty", lambda m: m["attestations"][0].update({"attester": ""}),
     "must not be empty"),
    ("dangling-claim-ref", lambda m: m["attestations"][0].update({"claim_ref": "nope"}),
     "names no claim"),
    ("agreement-relation", lambda m: m["attestations"][0].update(
        {"agreement_relation": "handshake"}), "not one of"),
    ("attestation-result", lambda m: m["attestations"][0].update({"result": "meh"}),
     "not one of"),
]


@pytest.mark.parametrize("label,mutate,fragment", _CASES, ids=[c[0] for c in _CASES])
def test_each_defect_is_reported_at_its_path(label, mutate, fragment):
    if label == "not-an-object":
        errors = manifest.validate([1, 2])
    else:
        errors = manifest.validate(mutated(mutate))
    assert any(fragment in e for e in errors), f"no error contains {fragment!r}: {errors}"


def test_identity_refuses_invalid_manifests():
    with pytest.raises(manifest.ManifestError, match="identity refused"):
        manifest.identity(mutated(lambda m: m.pop("weights")))


def test_loads_guards_the_canonical_domain_and_document_shape():
    assert manifest.loads('{"a": 1}') == {"a": 1}
    with pytest.raises(jcs.JCSError, match="duplicate"):
        manifest.loads('{"a": 1, "a": 2}')
    with pytest.raises(manifest.ManifestError, match="must be a JSON object"):
        manifest.loads("[1]")


# ----------------------------------------------------------------- identity properties


@given(st.integers(min_value=0, max_value=2**53 - 1))
def test_identity_is_order_independent_but_value_sensitive(seed):
    m = make_manifest()
    m["frame"]["a0_seed"] = seed
    reordered = dict(reversed(list(m.items())))
    assert manifest.identity(m) == manifest.identity(reordered)
    m2 = copy.deepcopy(m)
    m2["frame"]["rank"] = m["frame"]["rank"] + 1
    assert manifest.identity(m2) != manifest.identity(m)


# ----------------------------------------------------------------- schema lockstep


def test_packaged_schema_loads_and_declares_draft_2020_12():
    s = manifest.schema()
    assert s["$schema"].endswith("2020-12/schema")
    assert s["properties"]["schema_version"]["const"] == manifest.SCHEMA_VERSION


def _enum_of(s, *path):
    node = s
    for p in path:
        node = node[p]
    return tuple(node["enum"])


def test_schema_enums_match_validator_constants():
    s = manifest.schema()
    assert _enum_of(s, "properties", "frame", "properties",
                    "parameterization") == manifest.PARAMETERIZATIONS
    assert _enum_of(s, "properties", "provenance", "properties",
                    "generator_class") == manifest.GENERATOR_CLASSES
    claim = s["properties"]["claims"]["items"]["properties"]
    assert _enum_of(claim, "result") == manifest.CLAIM_RESULTS
    assert _enum_of(claim, "oracle_basis") == manifest.ORACLE_BASES
    assert _enum_of(claim, "verification", "properties",
                    "spec_provenance") == manifest.SPEC_PROVENANCES
    att = s["properties"]["attestations"]["items"]["properties"]
    assert _enum_of(att, "agreement_relation") == manifest.AGREEMENT_RELATIONS
    assert _enum_of(att, "result") == manifest.ATTESTATION_RESULTS


def test_schema_required_lists_and_patterns_match_the_validator():
    s = manifest.schema()
    assert set(s["required"]) == {
        "schema_version", "name", "version", "frame", "weights",
        "provenance", "claims", "attestations",
    }
    assert s["not"] == {"required": ["identity"]}
    assert s["properties"]["name"]["pattern"] == manifest.NAME_RE.pattern
    assert s["properties"]["version"]["pattern"] == manifest.VERSION_RE.pattern
    frame = s["properties"]["frame"]
    assert set(frame["required"]) == {"base_model", "a0_seed", "rank",
                                     "tokenizer_sha256", "parameterization"}
    assert frame["properties"]["tokenizer_sha256"]["pattern"] == manifest.HEX64_RE.pattern
    assert frame["properties"]["rank"]["minimum"] == 1
    assert frame["properties"]["rank"]["maximum"] == 65536
    # counter pairs: numerator/denominator names agree with COUNTER_PAIRS
    defs = s["$defs"]
    ver = s["properties"]["claims"]["items"]["properties"]["verification"]
    for pair_key, (num, den) in manifest.COUNTER_PAIRS.items():
        ref = ver["properties"][pair_key]["$ref"].rsplit("/", 1)[-1]
        assert set(defs[ref]["required"]) == {num, den}
    # forward compatibility is declared, not implied
    assert s["additionalProperties"] is True


def test_if_jsonschema_is_installed_it_agrees_on_the_corpus():
    """Executes the interop artifact with a real validator when one is present."""
    jsonschema = pytest.importorskip("jsonschema")
    v = jsonschema.Draft202012Validator(manifest.schema())
    assert list(v.iter_errors(make_manifest())) == []
    for label, mutate, _ in _CASES:
        if label in ("not-an-object", "not-canonicalizable", "task-id-duplicate",
                     "dangling-claim-ref", "mutation-pair-inverted", "spec-gap-inverted"):
            # Rules the JSON Schema deliberately does not encode: the canonical
            # domain, uniqueness, referential integrity, and cross-field
            # numerator<=denominator inequalities. validate() is the source of
            # truth for these; the schema document says so in its description.
            continue
        bad = mutated(mutate)
        assert not v.is_valid(bad), f"jsonschema accepts what validate() rejects: {label}"
