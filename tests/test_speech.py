"""Reading the document with the B2 labels."""

from pathlib import Path

import pytest

from disvimat.core.document import Character, Sign, Structure
from disvimat.core.speech import Speaker
from disvimat.core.tables import LabelEntry, load_table

DATA = Path(__file__).resolve().parents[1] / "data"


def speaker(language: str = "en") -> Speaker:
    return Speaker(load_table(DATA / f"labels.{language}.json", LabelEntry))


def test_sign() -> None:
    assert speaker().node(Sign("plus")) == "plus"


def test_adjacent_characters_are_grouped() -> None:
    nodes = [Character("1"), Character("2"), Sign("plus"), Character("3")]
    assert speaker().sequence(nodes) == "12 plus 3"


def test_fraction_with_parts() -> None:
    structure = Structure("fraction", [[Character("2")], [Character("3")]])
    assert speaker().node(structure) == "fraction 2 over 3 end of fraction"


def test_power_reads_the_base_first() -> None:
    structure = Structure("power", [[Character("x")], [Character("2")]])
    assert speaker().node(structure) == "x to the power of 2 end of exponent"


def test_empty_slot_is_spoken() -> None:
    structure = Structure("fraction", [[Character("2")], []])
    assert speaker().node(structure) == "fraction 2 over blank end of fraction"


def test_empty_sequence_is_a_blank() -> None:
    assert speaker().sequence([]) == "blank"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("es", "fracción 2 entre 3 fin de fracción"),
        ("fr", "fraction 2 sur 3 fin de fraction"),
    ],
)
def test_the_same_tree_speaks_in_every_language(language: str, expected: str) -> None:
    structure = Structure("fraction", [[Character("2")], [Character("3")]])
    assert speaker(language).node(structure) == expected
