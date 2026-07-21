"""Six-dot braille transcription driven by tables (B5/C3)."""

from pathlib import Path

import pytest

from disvimat.core.document import Character, Node, Sign, Structure
from disvimat.core.transcription.braille import (
    BrailleTablesMissing,
    BrailleTranscriber,
    braille_tables_available,
    create_transcriber,
)

DATA = Path(__file__).resolve().parents[1] / "data"


def transcriber() -> BrailleTranscriber:
    return create_transcriber(DATA, language="es")


def test_number_prefix_appears_once_per_run() -> None:
    nodes: list[Node] = [Character("1"), Character("2")]
    assert transcriber().unicode(nodes) == "⠼⠁⠃"


def test_a_space_restarts_the_number_run() -> None:
    nodes: list[Node] = [Character("1"), Character(" "), Character("2")]
    assert transcriber().unicode(nodes) == "⠼⠁⠀⠼⠃"


def test_letters_plain_and_capitals_prefixed() -> None:
    assert transcriber().unicode([Character("a"), Character("b")]) == "⠁⠃"
    assert transcriber().unicode([Character("A")]) == "⠨⠁"


def test_signs_come_from_the_table() -> None:
    nodes: list[Node] = [Character("1"), Sign("plus"), Character("2")]
    assert transcriber().unicode(nodes) == "⠼⠁⠖⠼⠃"


def test_fraction_uses_parts_and_prefixes_each_slot() -> None:
    nodes: list[Node] = [Structure("fraction", [[Character("1")], [Character("2")]])]
    assert transcriber().unicode(nodes) == "⠼⠁⠌⠼⠃"


def test_empty_slot_and_unknown_character_use_the_filler() -> None:
    assert transcriber().unicode([Structure("sqrt", [[]])]) == "⠩⠿⠴"
    assert transcriber().unicode([Character("@")]) == "⠿"


def test_ascii_bra_export() -> None:
    nodes: list[Node] = [Character("1"), Sign("plus"), Character("2")]
    assert transcriber().ascii(nodes) == "#a6#b"


def test_braille_never_falls_back_to_another_language() -> None:
    """Mathematical braille is normative per country: no cross-language reuse."""
    assert braille_tables_available(DATA, "es")
    assert not braille_tables_available(DATA, "fr")
    with pytest.raises(BrailleTablesMissing):
        create_transcriber(DATA, language="fr")
