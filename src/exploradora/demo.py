# SPDX-License-Identifier: AGPL-3.0-or-later
"""The demo library: two deterministic sample adapters, one honest failure.

How it works: ``build_demo_library()`` writes two adapter directories —
``demo-adapter``, which verifies clean, and ``tampered-adapter``, whose
weights are deliberately corrupted AFTER its manifest was written so that
``verify`` catches a real sha256 mismatch. The tampered one is the point of
the demo: exploradora's thesis is claims-you-can-check, and a demo that only
ever shows green would demonstrate nothing. Both manifests state plainly in
``training_data`` that they are not trained adapters.

Everything is deterministic (weights bytes come from a sha256 counter
stream keyed by the adapter's name; manifests go through the same
``core.scaffold`` path as user adapters), so two builds anywhere are
byte-identical and the demo is reproducible, not a lottery. The build is
idempotent by skip: an adapter directory that already has a manifest is left
untouched — the builder never deletes or rewrites user files.

The weights are STRUCTURALLY VALID safetensors written with the stdlib
(8-byte little-endian header length, JSON header, raw tensor data): no
safetensors dependency, and no lie in the file extension — a tool that
parses the format will read a real 4x4 F32 tensor of noise.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from exploradora.core import scaffold

#: Where `exploradora demo` builds its sample library by default.
DEFAULT_DEMO_DIR = Path.home() / ".exploradora" / "demo"

DEMO_ADAPTER = "demo-adapter"
TAMPERED_ADAPTER = "tampered-adapter"

WEIGHTS_FILENAME = "adapter.safetensors"

_NOT_TRAINED = (
    "none — deterministic pseudo-random bytes written by `exploradora demo`; "
    "NOT a trained adapter"
)


def _deterministic_bytes(seed: str, n: int) -> bytes:
    """A sha256 counter stream: same seed, same bytes, on any machine."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        out.extend(hashlib.sha256(f"{seed}:{counter}".encode()).digest())
        counter += 1
    return bytes(out[:n])


def write_minimal_safetensors(path: Path, *, seed: str) -> None:
    """A real (tiny) safetensors file: one 4x4 F32 tensor of deterministic noise."""
    data = _deterministic_bytes(seed, 4 * 4 * 4)  # 4x4 float32 = 64 bytes
    header = {
        "__metadata__": {"purpose": "exploradora demo fixture; not a trained adapter"},
        "demo.weight": {"dtype": "F32", "shape": [4, 4], "data_offsets": [0, len(data)]},
    }
    header_json = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(header_json)) + header_json + data)


def _build_adapter(adapter_dir: Path, name: str, *, training_data: str, tamper: bool) -> None:
    adapter_dir.mkdir(parents=True, exist_ok=True)
    weights_path = adapter_dir / WEIGHTS_FILENAME
    write_minimal_safetensors(weights_path, seed=name)
    scaffold.scaffold(
        adapter_dir,
        name=name,
        version=None,
        base_model="demo/none — these bytes target no real base model",
        a0_seed=0,
        rank=1,
        parameterization="lora",
        tokenizer_sha256=hashlib.sha256(b"exploradora demo tokenizer placeholder").hexdigest(),
        generator_class="human",
        training_data=training_data,
        license="CC0-1.0",
        weights_filename=WEIGHTS_FILENAME,
    )
    if tamper:
        # Corrupt the weights AFTER the manifest recorded their hash: this is
        # the adapter `verify` exists to catch, and the demo shows it honestly.
        blob = bytearray(weights_path.read_bytes())
        blob[-1] ^= 0xFF
        weights_path.write_bytes(bytes(blob))


def build_demo_library(library_dir: Path) -> tuple[Path, Path]:
    """Build (or leave untouched) the two sample adapters; returns their paths."""
    specs = (
        (DEMO_ADAPTER, _NOT_TRAINED, False),
        (
            TAMPERED_ADAPTER,
            _NOT_TRAINED + "; weights deliberately corrupted after manifest "
            "creation so verification has something real to catch",
            True,
        ),
    )
    paths = []
    for name, training_data, tamper in specs:
        adapter_dir = library_dir / name
        if not (adapter_dir / "manifest.json").is_file():
            _build_adapter(adapter_dir, name, training_data=training_data, tamper=tamper)
        paths.append(adapter_dir)
    return paths[0], paths[1]
