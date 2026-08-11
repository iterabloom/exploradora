# SPDX-License-Identifier: Apache-2.0
"""Adapter-directory verification: what was checked, what failed, what was not checked.

How it works: ``verify_dir()`` inspects an adapter directory (``manifest.json``
beside a weights file) and returns a tuple of ``Section`` results — one per
verification concern, in a fixed order — rather than a boolean. Each section
carries one of exactly three statuses:

- ``integrity-ok``      the check ran and passed
- ``integrity-failed``  the check ran and failed
- ``unchecked``         the check did not run, and the details say why

The three-way vocabulary is the honesty rule made structural: a bare
"verified" cannot be emitted because no such status exists, and a section that
could not run (weights can't be checked under an invalid manifest; claim
replay is not implemented in v0.1) says so instead of disappearing. Renderers
must show every section — the no-overall-green rule lives in the caller, but
this shape makes the dishonest rendering the harder one to write.

``ok_to_exit_zero()`` defines the scripting contract: zero iff no section
failed AND at least one was actually checked. "Nothing failed because nothing
ran" is exit code 1, not success.

Why hashing streams in chunks: weights files are tens of MB and may later be
GBs; reading them whole would make ``verify`` the first thing to fall over on
the artifacts it exists for.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from exploradora.core import jcs, manifest

MANIFEST_FILENAME = "manifest.json"

STATUS_OK = "integrity-ok"
STATUS_FAILED = "integrity-failed"
STATUS_UNCHECKED = "unchecked"

#: Fixed section order: schema first (everything depends on it), then weights,
#: then the claims placeholder so the not-checked surface is always visible.
SECTION_MANIFEST = "manifest-schema"
SECTION_WEIGHTS = "weights-integrity"
SECTION_CLAIMS = "claims"

_CHUNK = 1 << 20  # 1 MiB


@dataclass(frozen=True)
class Section:
    """One verification concern's outcome: its name, status, and the evidence."""

    name: str
    status: str
    details: tuple[str, ...]


def sha256_file(path: Path) -> str:
    """Streaming sha256 of a file's bytes, lowercase hex."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _unchecked(name: str, why: str) -> Section:
    return Section(name, STATUS_UNCHECKED, (why,))


def verify_dir(adapter_dir: Path) -> tuple[Section, ...]:
    """Verify one adapter directory. Always returns all three sections, in order."""
    claims_placeholder = _unchecked(
        SECTION_CLAIMS, "claim replay is not implemented in v0.1; claims were NOT checked"
    )

    manifest_path = adapter_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return (
            Section(SECTION_MANIFEST, STATUS_FAILED, (f"{MANIFEST_FILENAME} not found",)),
            _unchecked(SECTION_WEIGHTS, "cannot check weights: no manifest"),
            claims_placeholder,
        )

    try:
        doc = manifest.loads(manifest_path.read_bytes())
    except (jcs.JCSError, manifest.ManifestError) as exc:
        return (
            Section(SECTION_MANIFEST, STATUS_FAILED, (str(exc),)),
            _unchecked(SECTION_WEIGHTS, "cannot check weights: manifest unreadable"),
            claims_placeholder,
        )

    errors = manifest.validate(doc)
    if errors:
        return (
            Section(SECTION_MANIFEST, STATUS_FAILED, tuple(errors)),
            _unchecked(SECTION_WEIGHTS, "cannot check weights: manifest invalid"),
            claims_placeholder,
        )

    ident = manifest.identity(doc)
    manifest_section = Section(
        SECTION_MANIFEST, STATUS_OK, (f"schema_version 0 valid; identity {ident}",)
    )

    # The validator guarantees filename is a single path segment, so this join
    # cannot escape the adapter directory.
    weights_path = adapter_dir / doc["weights"]["filename"]
    if not weights_path.is_file():
        weights_section = Section(
            SECTION_WEIGHTS, STATUS_FAILED, (f"weights file {weights_path.name!r} not found",)
        )
    else:
        actual = sha256_file(weights_path)
        expected = doc["weights"]["sha256"]
        if actual == expected:
            weights_section = Section(
                SECTION_WEIGHTS, STATUS_OK, (f"sha256 matches manifest ({actual})",)
            )
        else:
            weights_section = Section(
                SECTION_WEIGHTS,
                STATUS_FAILED,
                (f"sha256 mismatch: manifest says {expected}", f"file bytes hash to {actual}"),
            )

    return (manifest_section, weights_section, claims_placeholder)


def ok_to_exit_zero(sections: tuple[Section, ...]) -> bool:
    """The scripting contract: no failures, and at least one check actually ran."""
    statuses = [s.status for s in sections]
    return STATUS_FAILED not in statuses and STATUS_OK in statuses
