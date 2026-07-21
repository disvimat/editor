"""Editor integration: typing the way an interface would."""

from pathlib import Path

import pytest

from disvimat.core.editor import Editor, create_editor
from disvimat.core.filters.mathml import MathMLFilter
from disvimat.export.xhtml import XHTMLExporter

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def editor() -> Editor:
    return create_editor(DATA)


def type_all(editor: Editor, strokes: list[str]) -> None:
    """Feed strokes the way an interface does: sign first, then character."""
    for stroke in strokes:
        if editor.press(stroke) is None and len(stroke) == 1:
            editor.type_character(stroke)


def test_typing_characters_and_signs(editor: Editor) -> None:
    editor.type_character("1")
    result = editor.press("+")
    assert result is not None
    assert result.text == "1+"
    assert result.position == 2
    assert result.speech == "plus"


def test_editing_a_fraction(editor: Editor) -> None:
    editor.type_character("1")
    editor.press("+")
    result = editor.press("Ctrl+F")
    assert result is not None
    assert result.text == "1+(□∕□)"
    assert result.position == result.text.index("□")
    assert result.speech == "fraction, blank 1"

    editor.type_character("2")
    result = editor.press("Tab")
    assert result is not None
    assert result.text == "1+(2∕□)"
    assert result.speech == "blank 2"

    editor.type_character("3")
    result = editor.press("Tab")  # last slot: it leaves the structure
    assert result is not None
    assert result.text == "1+(2∕3)"
    assert result.position == len(result.text)
    assert result.speech == "exit structure: fraction"


def test_read_line(editor: Editor) -> None:
    type_all(editor, ["1", "+", "Ctrl+F", "2", "Tab", "3"])
    result = editor.press("Ctrl+Shift+L")
    assert result is not None
    assert result.speech == "1 plus fraction 2 over 3 end of fraction"


def test_navigation_speaks_what_is_crossed(editor: Editor) -> None:
    editor.type_character("1")
    editor.press("+")
    result = editor.press("Left")
    assert result is not None
    assert result.speech == "plus"
    result = editor.press("Left")
    assert result is not None
    assert result.speech == "1"
    result = editor.press("Left")
    assert result is not None
    assert result.speech == "start of line"


def test_deleting_speaks_what_was_removed(editor: Editor) -> None:
    editor.type_character("1")
    editor.press("+")
    result = editor.press("Backspace")
    assert result is not None
    assert result.text == "1"
    assert result.speech == "backspace: plus"


def test_undo_and_redo(editor: Editor) -> None:
    editor.type_character("1")
    editor.type_character("2")
    result = editor.press("Ctrl+Z")
    assert result is not None
    assert result.text == "1"
    result = editor.press("Ctrl+Y")
    assert result is not None
    assert result.text == "12"


def test_unassigned_key_stroke(editor: Editor) -> None:
    assert editor.press("F9") is None
    assert editor.press("Ctrl+Alt+Q") is None


def test_numeric_keypad(editor: Editor) -> None:
    editor.type_character("1")
    result = editor.press("NumAdd")
    assert result is not None
    assert result.text == "1+"
    assert result.speech == "plus"


def test_importing_what_was_exported(editor: Editor) -> None:
    type_all(editor, ["1", "+", "Ctrl+F", "2", "Tab", "3"])
    document = XHTMLExporter(editor.catalog).xhtml_document(editor.document.root)

    receiver = create_editor(DATA)
    result = receiver.load(MathMLFilter(receiver.catalog).from_xhtml(document))
    assert result.text == "1+(2∕3)"
    assert result.position == len(result.text)
    assert result.speech == "1 plus fraction 2 over 3 end of fraction"

    # importing is undoable
    undone = receiver.press("Ctrl+Z")
    assert undone is not None
    assert undone.text == ""
