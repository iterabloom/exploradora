# SPDX-License-Identifier: AGPL-3.0-or-later
"""exploradora — local-first explorer for verifiable model adapters.

This is the package root for the client application: the TUI, the CLI entry
point, and (eventually) the exchange node. It is AGPL-3.0-or-later; the
schema/verification layer lives in the Apache-2.0 ``exploradora.core``
subpackage — see LICENSING.md at the repository root for why the split exists
and what it does (and does not) mean for users.

Pre-alpha: this skeleton exists so the license split is real on disk from the
first commits. The v0.1 implementation (manifest schema, verifier, TUI,
``init``/``verify``/``demo`` commands) has not landed yet — nothing here is
importable functionality, and the package is not on PyPI yet.
"""
