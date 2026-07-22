"""The native .dvm document format: round trip and validation."""

import pytest

from disvimat.core.document import Character, Line, Sign, Structure
from disvimat.core.dvm import DvmError, from_dvm, to_dvm


def sample() -> list[Line]:
    return [
        [Character("1"), Sign("plus"), Character("2")],
        [Structure("fraction", [[Character("3")], [Character("4"), Sign("minus")]])],
        [],  # an empty line survives too
    ]


def test_round_trip_preserves_the_tree() -> None:
    lines = sample()
    text = to_dvm(lines, language="es", profile="beginner")
    parsed = from_dvm(text)
    assert parsed.lines == lines
    assert parsed.language == "es"
    assert parsed.profile == "beginner"


def test_dvm_is_readable_json() -> None:
    text = to_dvm([[Character("1")]], language="en")
    assert '"format": "disvimat-document"' in text
    assert '"char": "1"' in text


def test_not_a_dvm_is_rejected() -> None:
    with pytest.raises(DvmError, match="not a DISVIMAT document"):
        from_dvm('{"format": "something-else"}')


def test_bad_json_is_rejected() -> None:
    with pytest.raises(DvmError, match="not valid JSON"):
        from_dvm("{ not json")


def test_unsupported_version_is_rejected() -> None:
    with pytest.raises(DvmError, match="unsupported version"):
        from_dvm('{"format": "disvimat-document", "version": 999, "lines": []}')


def test_empty_document_round_trips() -> None:
    parsed = from_dvm(to_dvm([[]], language="en"))
    assert parsed.lines == [[]]
