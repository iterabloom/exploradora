# SPDX-License-Identifier: Apache-2.0
"""exploradora.core — the schema/verification layer (Apache-2.0).

This subpackage will hold the parts of exploradora that are meant to spread
beyond the client and become a standard: the adapter manifest schema, frame
tags, canonical (RFC 8785 / JCS) serialization, and the hash/verify
primitives. It is permissively licensed (Apache-2.0) precisely so other
tools can adopt the format without adopting the client's AGPL terms; the
directory boundary IS the license boundary, enforced by
``scripts/license-headers``.

Design constraint inherited from that role: this layer must stay free of
dependencies on the client (no imports from ``exploradora`` outside ``core``),
so it can later be extracted as a separate ``exploradora-core`` distribution
without surgery.

Pre-alpha: no functionality has landed yet; this skeleton exists so the
license split is real on disk from the first commits.
"""
