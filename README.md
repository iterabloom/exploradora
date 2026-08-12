<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# exploradora

**STATUS: pre-alpha — v0.1.0 is [on PyPI](https://pypi.org/project/exploradora/):
a working local adapter-library explorer — the TUI (`exploradora` /
`exploradora browse`), `verify`, `init`, and `exploradora demo`. The
exchange, p2p, and claim replay are roadmap, not features.**

A local-first terminal UI for exploring, verifying, and managing small model
adapters — a package manager for *skills* instead of software, built so that
an adapter's claims are **checkable receipts, not marketing**.

The long-term thesis (see [VISION.md](VISION.md)): a frontier-class AI
system can be a *network* — a shared small base model on consumer hardware
plus community-minted adapters, each teaching one skill, each carrying
claims you can re-run. The client (this package) ships via PyPI as the
trusted computing base; adapters will ship via a peer-to-peer exchange as
untrusted content whose identity is a content hash. **PyPI ships code you
execute; the exchange ships weights you evaluate.** v0.1 is the seed of
that: the manifest schema those claims will live in, and a local explorer
that verifies what is checkable today.

## What v0.1 does

- **`exploradora`** / **`exploradora browse [dir]`** — the TUI: a table of
  the adapters in a library directory (default `~/.exploradora/library`)
  with a manifest detail pane. Every adapter starts as `unchecked`;
  pressing `v` verifies the selected one. Scanning reads — only
  verification verifies.
- **`exploradora verify <dir>`** — checks the manifest against schema v0
  and the weights file's sha256 against the manifest. Reports each concern
  separately in a three-word vocabulary — `integrity-ok` /
  `integrity-failed` / `unchecked` — and **never prints an overall verdict
  while anything is unchecked** (in v0.1, claim replay always is: it is not
  implemented, and the report says so instead of blessing it).
- **`exploradora init <dir>`** — scaffolds a valid `manifest.json` for an
  existing weights file. Hashes are computed; authored facts (base model,
  seed, rank, parameterization, tokenizer hash, license) are required
  flags, never guessed; claims start empty because no claim exists until
  something checked it. Whatever `init` writes, `verify` accepts.
- **`exploradora demo`** — builds two deterministic sample adapters and
  opens the browser on them: one valid, one whose weights were deliberately
  corrupted *after* its manifest was written, so verification has something
  real to catch. A demo that only showed green would demonstrate nothing.

The manifest schema is the release's most important artifact
(`exploradora.core.manifest` + a JSON Schema interop file, RFC 8785
canonical serialization, sha256 identity). Fields that could never be
retrofitted once adapters circulate are in it now, even though v0.1
verifies none of them: the one-way `parameterization` tag, a *graded*
`verification` block (never a boolean "verified"), `oracle_basis` per
claim, and `agreement_relation` per attestation.

## Install and try it

```sh
pip install exploradora
exploradora demo                    # the sample library, in the TUI
```

Or from source, for development:

```sh
git clone https://github.com/iterabloom/exploradora
cd exploradora
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/exploradora demo
```

Then make your own adapter explorable:

```sh
exploradora init ~/my-adapter \
  --base-model Qwen/Qwen2.5-Coder-1.5B-Instruct \
  --a0-seed 42 --rank 16 --parameterization lora \
  --tokenizer ~/my-adapter-tokenizer.json \
  --license Apache-2.0
exploradora verify ~/my-adapter
```

Python ≥ 3.10. One runtime dependency (`textual`, for the TUI).

## Roadmap (in roadmap voice — none of this exists yet)

- **Claim replay**: verifying an adapter's task claims by re-running them,
  locally, against the recipes its manifest names.
- **The exchange**: peer-to-peer adapter distribution — hash-addressed,
  permissionless, verified at install time on your machine.
- **Attestations**: publishing "I replayed this manifest's claims and
  agree" so redundant verification becomes accumulated evidence.
- **`check`**: the pip-check analog — inspecting an installed adapter set
  for adapters that contest each other's answers.

The research bets underneath these, with their honest current status, are
in [VISION.md](VISION.md).

## Licensing

Dual-licensed by directory (see [LICENSING.md](LICENSING.md)):
`src/exploradora/core/` — the schema/verification layer that should spread
and become a standard — is Apache-2.0; the client application (TUI, CLI,
demo) is AGPL-3.0-or-later.
