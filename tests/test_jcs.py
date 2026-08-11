# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the canonical serializer, including the properties AGENTS.md mandates.

How they work: hand-derived vectors pin the RFC 8785 clauses that have exact
expected outputs (escaping, the UTF-16 sorting example, integer bounds), and
Hypothesis properties cover what cannot be enumerated — round-trips, byte
stability, and insertion-order independence over the whole accepted domain.
The subjects are ``exploradora.core.jcs`` functions only (the core layer's
no-client-imports rule applies to test subjects too).
"""

from __future__ import annotations

import hashlib
import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from exploradora.core import jcs

# ----------------------------------------------------------------- vectors


def test_scalars_serialize_to_their_json_literals():
    assert jcs.dumps(None) == "null"
    assert jcs.dumps(True) == "true"
    assert jcs.dumps(False) == "false"
    assert jcs.dumps(0) == "0"
    assert jcs.dumps(-42) == "-42"


def test_escaping_follows_rfc_8785_exactly():
    # Shortcut escapes where they exist; \u00xx lowercase for other controls;
    # DEL (0x7F) and non-ASCII stay literal.
    assert jcs.dumps('\\ " \b \t \n \f \r') == '"\\\\ \\" \\b \\t \\n \\f \\r"'
    assert jcs.dumps("\x01\x1f") == '"\\u0001\\u001f"'
    assert jcs.dumps("\x7f€") == '"\x7f€"'


def test_object_keys_sort_by_utf16_code_units_not_code_points():
    """The RFC's one subtle clause, pinned with values where the orders differ.

    Code points: U+20AC (€) < U+FB33 (דּ) < U+1F600 (😀).
    UTF-16 units: 0x20AC (€) < 0xD83D.. (😀) < 0xFB33 (דּ).
    A naive sorted() would emit דּ before 😀 and change every downstream hash.
    """
    # Explicit escapes: an editor can silently store דּ decomposed (U+05D3 U+05BC),
    # which is a different string with a different sort position — measured, on
    # this file's own first draft.
    euro, emoji, dalet = "\u20ac", "\U0001f600", "\ufb33"
    doc = {dalet: 3, emoji: 2, euro: 1}
    assert jcs.dumps(doc) == f'{{"{euro}":1,"{emoji}":2,"{dalet}":3}}'
    assert sorted(doc) == [euro, dalet, emoji]      # naive code-point order...
    assert sorted(doc) != [euro, emoji, dalet]      # ...genuinely differs from UTF-16


def test_nested_structures_and_empty_containers():
    assert jcs.dumps({}) == "{}"
    assert jcs.dumps([]) == "[]"
    assert jcs.dumps({"": [{"b": [1, None]}, False]}) == '{"":[{"b":[1,null]},false]}'


def test_golden_hash_is_stable():
    """Identity = sha256 over dumps_bytes; this pin breaks loudly if bytes move."""
    doc = {"name": "demo", "n": 1, "tags": ["a", "б"]}
    digest = hashlib.sha256(jcs.dumps_bytes(doc)).hexdigest()
    assert jcs.dumps_bytes(doc) == b'{"n":1,"name":"demo","tags":["a","\xd0\xb1"]}'
    assert digest == hashlib.sha256(jcs.dumps(doc).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------- rejections


@pytest.mark.parametrize("n", [2**53, -(2**53), 2**60])
def test_integers_at_or_beyond_2_53_are_rejected(n):
    with pytest.raises(jcs.JCSError, match="2\\*\\*53"):
        jcs.dumps(n)
    with pytest.raises(jcs.JCSError, match="2\\*\\*53"):
        jcs.loads(str(n))


@pytest.mark.parametrize("n", [2**53 - 1, -(2**53) + 1])
def test_integers_just_inside_the_bound_pass(n):
    assert jcs.loads(jcs.dumps(n)) == n


def test_floats_are_rejected_everywhere():
    with pytest.raises(jcs.JCSError, match="float"):
        jcs.dumps(1.5)
    with pytest.raises(jcs.JCSError, match="float"):
        jcs.dumps({"x": [2.0]})  # integral-valued floats are still floats
    with pytest.raises(jcs.JCSError, match="float"):
        jcs.loads("[1.5]")
    with pytest.raises(jcs.JCSError, match="float"):
        jcs.loads("[1e2]")
    with pytest.raises(jcs.JCSError, match="float"):
        jcs.loads("[NaN]")


def test_bool_is_never_conflated_with_int():
    assert jcs.dumps([True, 1]) == "[true,1]"
    assert jcs.loads("[true,1]") == [True, 1]


def test_non_string_keys_and_unsupported_types_are_rejected():
    with pytest.raises(jcs.JCSError, match="key"):
        jcs.dumps({1: "a"})
    with pytest.raises(jcs.JCSError, match="no canonical form"):
        jcs.dumps({"x": b"bytes"})


def test_lone_surrogates_are_rejected_in_both_directions():
    with pytest.raises(jcs.JCSError, match="surrogate"):
        jcs.dumps("\ud800")
    with pytest.raises(jcs.JCSError, match="surrogate"):
        jcs.loads('"\\ud800"')  # json.loads happily produces these; we must not
    with pytest.raises(jcs.JCSError, match="surrogate"):
        jcs.loads('{"\\udc00": 1}')


def test_duplicate_keys_are_rejected_at_any_depth():
    with pytest.raises(jcs.JCSError, match="duplicate"):
        jcs.loads('{"a": 1, "a": 2}')
    with pytest.raises(jcs.JCSError, match="duplicate"):
        jcs.loads('[{"x": {"b": 1, "b": 1}}]')


def test_invalid_json_reports_as_jcs_error():
    with pytest.raises(jcs.JCSError, match="not valid JSON"):
        jcs.loads("{nope")
    with pytest.raises(jcs.JCSError, match="not valid JSON"):
        jcs.loads(b"\xff\xfe")  # undecodable bytes


# ----------------------------------------------------------------- properties

# The accepted domain: what a manifest (with arbitrary unknown fields) may hold.
_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**53) + 1, max_value=2**53 - 1),
    st.text(alphabet=st.characters(exclude_categories=("Cs",))),  # no surrogates
)
_values = st.recursive(
    _scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(
            st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=8),
            children,
            max_size=4,
        ),
    ),
    max_leaves=20,
)


@given(_values)
def test_round_trip_preserves_the_value(value):
    assert jcs.loads(jcs.dumps(value)) == value


@given(_values)
def test_reserialization_is_byte_stable(value):
    """AGENTS.md's preserve-plus-reserialize rule, as a property."""
    once = jcs.dumps_bytes(value)
    assert jcs.dumps_bytes(jcs.loads(once)) == once


@given(_values)
def test_canonical_output_is_valid_json_for_any_parser(value):
    assert json.loads(jcs.dumps(value)) is not None or value is None


@given(st.dictionaries(st.text(max_size=6), _scalars, max_size=6))
def test_insertion_order_never_changes_the_bytes(d):
    reordered = dict(reversed(list(d.items())))
    assert jcs.dumps_bytes(d) == jcs.dumps_bytes(reordered)
