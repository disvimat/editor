"""Localisation (E6): language tables, fallback and interface strings."""

from pathlib import Path

import pytest

from disvimat.core.editor import create_editor
from disvimat.core.tables import language_table_path
from disvimat.core.ui_text import UIText

DATA = Path(__file__).resolve().parents[1] / "data"


def test_language_table_resolves_the_requested_language() -> None:
    assert language_table_path(DATA, "labels", "es").name == "labels.es.json"
    assert language_table_path(DATA, "labels", "fr").name == "labels.fr.json"


def test_missing_language_falls_back_to_the_reference_one() -> None:
    assert language_table_path(DATA, "labels", "de").name == "labels.en.json"


@pytest.mark.parametrize(
    ("language", "expected"),
    [("en", "plus"), ("es", "más"), ("fr", "plus")],
)
def test_the_editor_speaks_every_language(language: str, expected: str) -> None:
    editor = create_editor(DATA, language=language)
    result = editor.press("+")
    assert result is not None
    assert result.speech == expected


def test_editor_in_an_unsupported_language_falls_back() -> None:
    editor = create_editor(DATA, language="de")
    result = editor.press("+")
    assert result is not None
    assert result.speech == "plus"  # English reference


@pytest.mark.parametrize(
    ("language", "expected"),
    [("en", "Calculate"), ("es", "Calcular"), ("fr", "Calculer")],
)
def test_interface_strings_are_localised(language: str, expected: str) -> None:
    text = UIText.load(DATA, language=language)
    assert text("button_calculate") == expected


def test_interface_placeholders_are_substituted() -> None:
    text = UIText.load(DATA, language="en")
    assert text("status_exported", path="/tmp/a.xhtml") == "Exported: /tmp/a.xhtml"


def test_unknown_interface_id_falls_back_to_the_id() -> None:
    text = UIText.load(DATA, language="en")
    assert text("no_such_string") == "no_such_string"
