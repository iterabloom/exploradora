# SPDX-License-Identifier: Apache-2.0
"""Manifest scaffolding for `exploradora init`: make an existing adapter explorable.

How it works: ``scaffold()`` takes a directory holding a weights file plus the
authored facts about the adapter (frame tag, provenance, license), computes
what is computable (the weights sha256, streamed; the default name from the
directory), assembles a schema_version-0 manifest with EMPTY ``claims`` and
``attestations``, validates it with the same ``manifest.validate()`` that
``verify`` uses, and only then writes ``manifest.json`` — pretty-printed for
human editing (identity is computed over the JCS form, so formatting is
free). Any failure raises ``ScaffoldError`` before the write: init never
leaves a half-manifest behind and never overwrites one that exists.

Why the defaults are shaped this way: authored facts (base model, seed, rank,
parameterization, tokenizer hash, license) have no honest default — a guessed
value would be fabricated metadata, so the CLI requires them as flags.
``generator_class`` may default only because the schema has an explicit
``"unknown"`` member for exactly this; claims start empty because no claim
exists until something checked it. The contract is: **whatever init writes,
verify accepts** — the scaffold path and the verification path share one
validator, so they cannot drift.

Weights detection: an explicit filename wins; otherwise the sole non-hidden
file (besides ``manifest.json``) is taken, or the sole ``*.safetensors``
among several files; anything still ambiguous is an error naming every
candidate rather than a guess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exploradora.core import manifest, verify

SAFETENSORS_SUFFIX = ".safetensors"

DEFAULT_VERSION = "0.0.0"


class ScaffoldError(ValueError):
    """Raised when a manifest cannot be scaffolded; the message says why, fully."""


def detect_weights(adapter_dir: Path, explicit: str | None) -> str:
    """The weights filename to record: explicit choice, sole candidate, or error."""
    if explicit is not None:
        if not (adapter_dir / explicit).is_file():
            raise ScaffoldError(f"weights file {explicit!r} not found in {adapter_dir}")
        return explicit
    candidates = sorted(
        p.name
        for p in adapter_dir.iterdir()
        if p.is_file() and p.name != verify.MANIFEST_FILENAME and not p.name.startswith(".")
    )
    if not candidates:
        raise ScaffoldError(f"no weights file found in {adapter_dir}")
    if len(candidates) == 1:
        return candidates[0]
    safetensors = [name for name in candidates if name.endswith(SAFETENSORS_SUFFIX)]
    if len(safetensors) == 1:
        return safetensors[0]
    raise ScaffoldError(
        f"cannot choose a weights file among {', '.join(candidates)} — pass --weights"
    )


def scaffold(
    adapter_dir: Path,
    *,
    name: str | None,
    version: str | None,
    base_model: str,
    a0_seed: int,
    rank: int,
    parameterization: str,
    tokenizer_sha256: str,
    generator_class: str,
    training_data: str,
    license: str,  # noqa: A002 — the manifest field's own name beats the builtin
    weights_filename: str | None,
) -> tuple[dict[str, Any], str]:
    """Validate-then-write ``manifest.json``; returns (manifest, identity)."""
    if not adapter_dir.is_dir():
        raise ScaffoldError(f"{adapter_dir} is not a directory")
    manifest_path = adapter_dir / verify.MANIFEST_FILENAME
    if manifest_path.exists():
        raise ScaffoldError(f"{manifest_path} already exists; init never overwrites a manifest")

    fname = detect_weights(adapter_dir, weights_filename)
    doc: dict[str, Any] = {
        "schema_version": manifest.SCHEMA_VERSION,
        "name": name if name is not None else adapter_dir.resolve().name,
        "version": version if version is not None else DEFAULT_VERSION,
        "frame": {
            "base_model": base_model,
            "a0_seed": a0_seed,
            "rank": rank,
            "tokenizer_sha256": tokenizer_sha256,
            "parameterization": parameterization,
        },
        "weights": {
            "filename": fname,
            "sha256": verify.sha256_file(adapter_dir / fname),
        },
        "provenance": {
            "generator_class": generator_class,
            "training_data": training_data,
            "license": license,
        },
        "claims": [],
        "attestations": [],
    }

    errors = manifest.validate(doc)
    if errors:
        raise ScaffoldError(
            "scaffold refused — these flag values produce an invalid manifest:\n"
            + "\n".join(errors)
        )

    manifest_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc, manifest.identity(doc)
