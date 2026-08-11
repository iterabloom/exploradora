<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# LICENSING.md

This repository is dual-licensed by directory. Every source file carries an
SPDX header declaring its license; `scripts/license-headers` enforces the map
below (and the pre-commit hook runs it).

| Path | License | Full text |
|---|---|---|
| `src/exploradora/core/` | Apache-2.0 | `LICENSE-APACHE` (root), `src/exploradora/core/LICENSE` |
| everything else | AGPL-3.0-or-later | `LICENSE` (root) |

## Why the split

- **`core/` (Apache-2.0)** is the schema/verification layer: the manifest
  schema, frame tags, canonical serialization, and hash/verify primitives.
  This layer is meant to spread everywhere and become a standard, so it is
  permissively licensed.
- **Everything else (AGPL-3.0-or-later)** is the client application — the TUI
  and, eventually, the exchange node — plus the development tooling. Copyleft
  here is capture-resistance for the network's front door. (AGPL §13's reach
  over p2p nodes serving peers is unsettled law; this choice is a values
  statement as much as a legal mechanism.)

## Honesty note

Within a single installed wheel, the combined work is effectively
AGPL-3.0-or-later for application users. The near-term value of the split is
clean provenance and the planned future extraction of `core/` as a separate
`exploradora-core` distribution under Apache-2.0. Installing `exploradora`
today does **not** give you an Apache-licensed client library.

## Contributions

All commits are signed off under the Developer Certificate of Origin (`DCO`).
Sign-offs certify origin under the license of the directory being modified at
the time of contribution; they grant no relicensing rights. This is why the
split exists on disk from the first commit rather than being deferred: once
outside contributions land in an AGPL tree, it cannot be relicensed without
unanimous contributor consent.

## Provenance

Portions of the development tooling (`scripts/`, `.githooks/`, `.woodpecker/`,
governance documents) are adapted from the
[hypergumbo](https://github.com/iterabloom/hypergumbo) project
(AGPL-3.0-or-later, same maintainer) and remain AGPL-3.0-or-later here.
