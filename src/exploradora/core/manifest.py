# SPDX-License-Identifier: Apache-2.0
"""Adapter manifest schema v0: validation and identity.

How it works: ``validate()`` walks a parsed manifest and returns a list of
error strings ("path: problem"), empty iff valid — a list rather than an
exception so a caller can show every defect at once. ``identity()`` is the
sha256 of the manifest's RFC 8785 (JCS) serialization and refuses invalid
manifests, because the identity of a malformed record pins nothing. The
JSON Schema beside this module (``manifest.schema.json``) is the
interoperability artifact; *this* module is the executable source of truth,
and a unit test keeps the two in lockstep field for field.

Why these fields exist — the four that cannot be retrofitted once manifests
circulate, per the project brief:

- ``frame.parameterization``: LoRA converts to DoRA exactly but not back, so
  two adapters with identical frame tags and different parameterizations are
  neither comparable nor mergeable; without the field nothing would say so.
- ``claims[].verification``: a *graded* block — mutation kill counts,
  property coverage, spec-gap probes, spec provenance — never a boolean
  ``verified`` flag. Oracle strength is an axis; a boolean asserts more than
  the evidence supports. Counters are integer pairs (numerator ≤ denominator)
  and a zero denominator **means unmeasured** — explicit gaps over implicit
  completeness. The spec-gap count is a lower bound: "no gap found" never
  means "proved faithful".
- ``claims[].oracle_basis``: whether the claim was checked against an
  executable oracle or is merely coherent within a stance. Without this, a
  confidently self-consistent wrong adapter presents exactly like a verified
  one.
- ``attestations[].agreement_relation``: what "agreed" *means* — bitwise
  identity, a canonical reference stack, a numeric tolerance, or
  verdict-level agreement. An attestation that does not say cannot be
  weighed against one that does.

Field axes (per the schema discipline; the four-way taxonomy has no integer
axis, so integer fields are annotated as components of the axis they serve
rather than silently given a fifth kind):

======================================  ==========================================
field                                   axis
======================================  ==========================================
schema_version                          bounded-enum (integers; only 0 today)
name, version                           identity (pattern-bounded)
frame.base_model                        identity component
frame.a0_seed, frame.rank               identity component (integer)
frame.tokenizer_sha256                  hash — sha256 of the tokenizer file bytes
frame.parameterization                  bounded-enum: lora | dora
weights.filename                        identity component (single path segment)
weights.sha256                          hash — sha256 of the weights file bytes
provenance.generator_class              bounded-enum
provenance.training_data                free-text (description; no consumer branches)
provenance.license                      free-text (SPDX expression recommended)
claims[].task_id                        identity (unique within the manifest)
claims[].result                         bounded-enum: pass | fail
claims[].io_sha256                      hash — sha256 of the claim's I/O transcript
                                        bytes as produced by the recipe that
                                        recipe_note names
claims[].recipe_note                    free-text (names the recipe; provenance)
claims[].verification.*                 integer pairs + bounded-enum (see above)
claims[].oracle_basis                   bounded-enum
attestations[].attester                 identity (of the attesting party)
attestations[].claim_ref                identity reference → claims[].task_id
attestations[].agreement_relation       bounded-enum
attestations[].result                   bounded-enum: agree | disagree
======================================  ==========================================

Forward compatibility: unknown fields are preserved and legal at every level,
constrained only by the canonical-form rules (integers under 2**53, no
floats, no lone surrogates) — enforced here by requiring the whole manifest
to be JCS-serializable. The top-level key ``identity`` is reserved and
rejected: the manifest never embeds its own hash.
"""

from __future__ import annotations

import hashlib
import json
import re
from importlib import resources
from typing import Any

from exploradora.core import jcs

SCHEMA_VERSION = 0

#: The reserved top-level key: identity is computed over the manifest, never stored in it.
RESERVED_TOP_LEVEL = frozenset({"identity"})

PARAMETERIZATIONS = ("lora", "dora")
GENERATOR_CLASSES = ("human", "local", "hosted", "frontier", "mixed", "unknown")
CLAIM_RESULTS = ("pass", "fail")
SPEC_PROVENANCES = ("upstream-suite", "authored-from-spec", "minted", "unknown")
ORACLE_BASES = ("executable-oracle", "stance-coherent")
AGREEMENT_RELATIONS = ("bitwise", "reference-stack", "numeric-tolerance", "verdict-level")
ATTESTATION_RESULTS = ("agree", "disagree")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

#: (numerator key, denominator key) for each graded-verification counter pair.
COUNTER_PAIRS = {
    "mutation": ("killed", "total"),
    "property_coverage": ("covered", "total"),
    "spec_gap": ("found", "probed"),
}


class ManifestError(ValueError):
    """Raised by identity() when asked to hash a manifest that does not validate."""


def schema() -> dict[str, Any]:
    """The packaged JSON Schema document (the interoperability artifact)."""
    text = resources.files("exploradora.core").joinpath("manifest.schema.json").read_text("utf-8")
    return json.loads(text)


# ------------------------------------------------------------------ helpers

def _need(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> bool:
    if key not in obj:
        errors.append(f"{path}.{key}: required field missing")
        return False
    return True


def _str(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> str | None:
    if not _need(obj, key, path, errors):
        return None
    v = obj[key]
    if not isinstance(v, str):
        errors.append(f"{path}.{key}: expected string, got {type(v).__name__}")
        return None
    return v


def _int(obj: dict[str, Any], key: str, path: str, errors: list[str],
         lo: int, hi: int) -> int | None:
    if not _need(obj, key, path, errors):
        return None
    v = obj[key]
    # bool is an int subclass; True where an integer belongs is a type error, not 1.
    if isinstance(v, bool) or not isinstance(v, int):
        errors.append(f"{path}.{key}: expected integer, got {type(v).__name__}")
        return None
    if not lo <= v <= hi:
        errors.append(f"{path}.{key}: {v} outside [{lo}, {hi}]")
        return None
    return v


def _enum(obj: dict[str, Any], key: str, path: str, errors: list[str],
          allowed: tuple[str, ...]) -> None:
    v = _str(obj, key, path, errors)
    if v is not None and v not in allowed:
        errors.append(f"{path}.{key}: {v!r} not one of {list(allowed)}")


def _hex64(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    v = _str(obj, key, path, errors)
    if v is not None and not HEX64_RE.match(v):
        errors.append(f"{path}.{key}: not 64 lowercase hex chars")


def _obj(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> dict[str, Any] | None:
    if not _need(parent, key, path, errors):
        return None
    v = parent[key]
    if not isinstance(v, dict):
        errors.append(f"{path}.{key}: expected object, got {type(v).__name__}")
        return None
    return v


def _counter_pair(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    """An integer pair numerator ≤ denominator; denominator 0 means unmeasured."""
    pair = _obj(parent, key, path, errors)
    if pair is None:
        return
    num_key, den_key = COUNTER_PAIRS[key]
    here = f"{path}.{key}"
    num = _int(pair, num_key, here, errors, 0, jcs.MAX_INT - 1)
    den = _int(pair, den_key, here, errors, 0, jcs.MAX_INT - 1)
    if num is not None and den is not None and num > den:
        errors.append(f"{here}: {num_key} {num} exceeds {den_key} {den}")


# ------------------------------------------------------------------ validate

def validate(manifest: Any) -> list[str]:
    """Every problem with ``manifest``, as "path: problem" strings; [] iff valid."""
    if not isinstance(manifest, dict):
        return [f"$: expected object, got {type(manifest).__name__}"]
    errors: list[str] = []

    # Canonical-form rules cover UNKNOWN fields too: if it cannot be JCS-serialized
    # (floats, oversized ints, surrogates, non-string keys anywhere), it is invalid.
    try:
        jcs.dumps(manifest)
    except jcs.JCSError as exc:
        errors.append(f"$: not canonicalizable — {exc}")

    for reserved in sorted(RESERVED_TOP_LEVEL & manifest.keys()):
        errors.append(f"$.{reserved}: reserved — the manifest never embeds its own hash")

    ver = _int(manifest, "schema_version", "$", errors, 0, jcs.MAX_INT - 1)
    if ver is not None and ver != SCHEMA_VERSION:
        errors.append(f"$.schema_version: {ver} is not the supported version {SCHEMA_VERSION}")

    name = _str(manifest, "name", "$", errors)
    if name is not None and not NAME_RE.match(name):
        errors.append("$.name: must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    version = _str(manifest, "version", "$", errors)
    if version is not None and not VERSION_RE.match(version):
        errors.append("$.version: must match ^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")

    frame = _obj(manifest, "frame", "$", errors)
    if frame is not None:
        base = _str(frame, "base_model", "$.frame", errors)
        if base is not None and not 1 <= len(base) <= 256:
            errors.append("$.frame.base_model: length outside [1, 256]")
        _int(frame, "a0_seed", "$.frame", errors, 0, jcs.MAX_INT - 1)
        _int(frame, "rank", "$.frame", errors, 1, 65536)
        _hex64(frame, "tokenizer_sha256", "$.frame", errors)
        _enum(frame, "parameterization", "$.frame", errors, PARAMETERIZATIONS)

    weights = _obj(manifest, "weights", "$", errors)
    if weights is not None:
        fname = _str(weights, "filename", "$.weights", errors)
        if fname is not None and (
            not 1 <= len(fname) <= 255
            or "/" in fname or "\\" in fname or fname in (".", "..")
        ):
            errors.append("$.weights.filename: must be a single path segment (no separators)")
        _hex64(weights, "sha256", "$.weights", errors)

    prov = _obj(manifest, "provenance", "$", errors)
    if prov is not None:
        _enum(prov, "generator_class", "$.provenance", errors, GENERATOR_CLASSES)
        _str(prov, "training_data", "$.provenance", errors)
        lic = _str(prov, "license", "$.provenance", errors)
        if lic is not None and not lic:
            errors.append("$.provenance.license: must not be empty")

    task_ids: set[str] = set()
    claims = manifest.get("claims")
    if not isinstance(claims, list):
        errors.append("$.claims: required field missing or not an array")
    else:
        for i, claim in enumerate(claims):
            path = f"$.claims[{i}]"
            if not isinstance(claim, dict):
                errors.append(f"{path}: expected object, got {type(claim).__name__}")
                continue
            tid = _str(claim, "task_id", path, errors)
            if tid is not None:
                if not tid:
                    errors.append(f"{path}.task_id: must not be empty")
                elif tid in task_ids:
                    errors.append(f"{path}.task_id: duplicate {tid!r}")
                task_ids.add(tid)
            _enum(claim, "result", path, errors, CLAIM_RESULTS)
            _hex64(claim, "io_sha256", path, errors)
            _str(claim, "recipe_note", path, errors)
            verification = _obj(claim, "verification", path, errors)
            if verification is not None:
                for pair_key in COUNTER_PAIRS:
                    _counter_pair(verification, pair_key, f"{path}.verification", errors)
                _enum(verification, "spec_provenance", f"{path}.verification",
                      errors, SPEC_PROVENANCES)
            _enum(claim, "oracle_basis", path, errors, ORACLE_BASES)

    attestations = manifest.get("attestations")
    if not isinstance(attestations, list):
        errors.append("$.attestations: required field missing or not an array")
    else:
        for i, att in enumerate(attestations):
            path = f"$.attestations[{i}]"
            if not isinstance(att, dict):
                errors.append(f"{path}: expected object, got {type(att).__name__}")
                continue
            attester = _str(att, "attester", path, errors)
            if attester is not None and not attester:
                errors.append(f"{path}.attester: must not be empty")
            ref = _str(att, "claim_ref", path, errors)
            if ref is not None and ref not in task_ids:
                errors.append(f"{path}.claim_ref: {ref!r} names no claim task_id")
            _enum(att, "agreement_relation", path, errors, AGREEMENT_RELATIONS)
            _enum(att, "result", path, errors, ATTESTATION_RESULTS)

    return errors


# ------------------------------------------------------------------ identity

def identity(manifest: dict[str, Any]) -> str:
    """sha256 hex of the manifest's canonical bytes. Refuses invalid manifests.

    Unknown fields participate in the hash — they are content, and preserving
    them while excluding them from identity would let two different documents
    share one name.
    """
    errors = validate(manifest)
    if errors:
        raise ManifestError(
            f"identity refused: manifest has {len(errors)} validation error(s); first: {errors[0]}"
        )
    return hashlib.sha256(jcs.dumps_bytes(manifest)).hexdigest()


def loads(text: str | bytes) -> dict[str, Any]:
    """Parse manifest JSON with the canonical-domain guards; validation is separate.

    Split on purpose: ``loads`` answers "is this well-formed JSON in the
    canonical domain", ``validate`` answers "is it a manifest" — so a caller
    can report parse problems and schema problems distinctly.
    """
    value = jcs.loads(text)
    if not isinstance(value, dict):
        raise ManifestError(f"manifest document must be a JSON object, got {type(value).__name__}")
    return value
