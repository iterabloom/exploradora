# SPDX-License-Identifier: Apache-2.0
"""RFC 8785 (JCS) canonical JSON, restricted to the manifest domain.

How it works: ``dumps()`` walks a JSON-compatible Python value and emits the
canonical text form directly — object keys sorted by UTF-16 code units,
minimal string escaping, no whitespace — and ``loads()`` parses JSON while
rejecting everything whose canonical form would be ambiguous or lossy
(duplicate keys, floats, lone surrogates). ``dumps_bytes()`` is the UTF-8
encoding of ``dumps()`` and is the byte-domain over which manifest identity
hashes are computed.

Why a restricted profile instead of full RFC 8785: the repository's schema
discipline confines all numbers to integers with |n| < 2**53 (ratios travel
as integer pairs), which removes the ES6 float-formatting clause — the one
genuinely hard part of JCS — from the trusted surface entirely. What remains
is small enough to implement from the standard library and property-test
exhaustively, which matters because this module defines identity: two
manifests are the same adapter iff these bytes hash the same.

The subtle clause kept from the RFC: keys sort by UTF-16 **code units**, not
Unicode code points. The two orders disagree exactly where a BMP character
above U+D7FF meets a supplementary-plane character (e.g. ``"דּ"`` U+FB33 vs
``"😀"`` U+1F600: code points say דּ < 😀, UTF-16 units say 😀 < דּ), so a
naive ``sorted()`` would produce different bytes — and a different identity —
for the same manifest. The sort key is therefore the UTF-16BE encoding.

This layer must stay importable without the AGPL client package and without
third-party dependencies (see ``exploradora.core.__init__``).
"""

from __future__ import annotations

import json
from typing import Any

#: JSON interoperability bound (RFC 8785 §3.2.2.3 via the repo's integer rule):
#: integers must satisfy |n| < 2**53 so every consumer, ES6 included, reads
#: the same value.
MAX_INT = 2**53

#: The two-character escapes RFC 8785 §3.2.2.2 requires where they exist.
_SHORT_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


class JCSError(ValueError):
    """A value outside the canonical domain: nothing here is representable ambiguously."""


def _check_string(s: str) -> str:
    """Reject lone surrogates: their UTF-8/UTF-16 encodings are not well-formed.

    ``json.loads`` will happily produce them from ``\\ud800`` escapes, and
    ``str.encode`` then fails — at hashing time, far from the cause. Rejecting
    them here keeps "accepted by jcs" equivalent to "hashable by jcs".
    """
    for ch in s:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            raise JCSError(f"lone surrogate U+{ord(ch):04X} in string {s!r:.40}")
    return s


def _escape(s: str) -> str:
    """RFC 8785 §3.2.2.2: shortcut escapes, \\u00xx for other controls, rest literal."""
    out: list[str] = []
    for ch in s:
        if ch in _SHORT_ESCAPES:
            out.append(_SHORT_ESCAPES[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    return "".join(out)


def _key(s: str) -> bytes:
    """The RFC's sort key: the string as UTF-16 code units, compared bytewise."""
    return s.encode("utf-16-be")


def _emit(value: Any, out: list[str]) -> None:
    # bool must be tested before int: Python's bool is an int subclass, and
    # serializing True as 1 would silently merge two distinct JSON values.
    if value is None:
        out.append("null")
    elif isinstance(value, bool):
        out.append("true" if value else "false")
    elif isinstance(value, int):
        if not -MAX_INT < value < MAX_INT:
            raise JCSError(f"integer {value} outside |n| < 2**53")
        out.append(str(value))
    elif isinstance(value, float):
        raise JCSError(
            f"float {value!r} rejected: manifest numbers are integers "
            "(encode ratios as integer pairs)"
        )
    elif isinstance(value, str):
        out.append(f'"{_escape(_check_string(value))}"')
    elif isinstance(value, list):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _emit(item, out)
        out.append("]")
    elif isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise JCSError(f"object key {k!r} is {type(k).__name__}, not str")
        out.append("{")
        for i, k in enumerate(sorted(value, key=_key)):
            if i:
                out.append(",")
            out.append(f'"{_escape(_check_string(k))}":')
            _emit(value[k], out)
        out.append("}")
    else:
        raise JCSError(f"type {type(value).__name__} has no canonical form")


def dumps(value: Any) -> str:
    """The canonical (RFC 8785, integer-restricted) serialization of ``value``."""
    out: list[str] = []
    _emit(value, out)
    return "".join(out)


def dumps_bytes(value: Any) -> bytes:
    """UTF-8 bytes of ``dumps(value)`` — the byte-domain manifest identity hashes over."""
    return dumps(value).encode("utf-8")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for k, v in pairs:
        if k in obj:
            raise JCSError(f"duplicate object key {k!r}")
        obj[k] = v
    return obj


def _reject_float(text: str) -> Any:
    raise JCSError(f"float literal {text!r} rejected: manifest numbers are integers")


def _walk_check(value: Any) -> Any:
    """Post-parse validation so ``loads`` accepts exactly what ``dumps`` accepts."""
    if isinstance(value, str):
        _check_string(value)
    elif isinstance(value, bool):
        pass
    elif isinstance(value, int) and not -MAX_INT < value < MAX_INT:
        raise JCSError(f"integer {value} outside |n| < 2**53")
    elif isinstance(value, list):
        for item in value:
            _walk_check(item)
    elif isinstance(value, dict):
        for k, v in value.items():
            _check_string(k)
            _walk_check(v)
    return value


def loads(text: str | bytes) -> Any:
    """Parse JSON, rejecting anything whose canonical form would be ambiguous.

    Rejected: duplicate object keys (silent last-wins would let two different
    texts share one identity), floats and the non-finite constants (the
    integer rule applies to *unknown* fields too), integers at or beyond
    2**53, and lone surrogates. The result round-trips: for any accepted
    ``text``, ``dumps(loads(text))`` succeeds, and for canonical input it is
    byte-identical.
    """
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except JCSError:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JCSError(f"not valid JSON: {exc}") from exc
    return _walk_check(value)
