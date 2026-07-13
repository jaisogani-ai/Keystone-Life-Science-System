"""
Release-gate: Claude structured output is schema-validated. Malformed / partial
model output must be rejected so the caller falls back to the deterministic
reasoner (never a fabricated field).
"""
from keystone.agents.claude_reasoner import _valid_schema


def test_valid_when_all_required_keys_present_and_nonnull():
    assert _valid_schema({"statement": "x", "mechanism_path": ["N_a"]},
                         ("statement", "mechanism_path"))


def test_invalid_when_a_required_key_is_missing():
    assert not _valid_schema({"statement": "x"}, ("statement", "mechanism_path"))


def test_invalid_when_a_required_key_is_null():
    assert not _valid_schema({"weakness": None}, ("weakness",))


def test_invalid_when_not_a_dict():
    assert not _valid_schema("not json", ("weakness",))
    assert not _valid_schema(None, ("weakness",))
    assert not _valid_schema(["a", "b"], ("weakness",))


def test_no_required_keys_accepts_any_dict():
    assert _valid_schema({}, ())
