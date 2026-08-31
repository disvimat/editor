"""Multi-line documents: new lines, line navigation, merging and rendering."""

from pathlib import Path

import pytest

from disvimat.core.document import Character, Document, Sign
from disvimat.core.editor import create_editor
from disvimat.core.presentation import Presenter
from disvimat.core.tables import GlyphEntry, load_table

DATA = Path(__file__).resolve().parents[1] / "data"


def presenter() -> Presenter:
    return Presenter(load_table(DATA / "glyphs.json", GlyphEntry))


# --- document model ---------------------------------------------------------


def test_new_line_splits_at_the_cursor() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(Character("2"))
    document.left()  # cursor between 1 and 2
    assert document.new_line()
    assert document.line_count() == 2
    assert document.lines[0] == [Character("1")]
    assert document.lines[1] == [Character("2")]
    assert document.cursor_line() == 1
    assert document.cursor_index() == 0


def test_line_navigation_at_top_level() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    assert document.cursor_line() == 1
    assert document.line_up()
    assert document.cursor_line() == 0
    assert document.line_down()
    assert document.cursor_line() == 1
    assert not document.line_down()  # already the last line


def test_backspace_at_line_start_merges() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    document.to_line_start()  # start of second line
    assert document.backspace() is None  # nothing to delete within the line
    assert document.merge_with_previous_line()
    assert document.line_count() == 1
    assert document.lines[0] == [Character("1"), Character("2")]
    assert document.cursor_index() == 1


def test_new_line_is_inert_inside_a_structure() -> None:
    from disvimat.core.document import Structure

    document = Document()
    document.insert(Structure("fraction", [[], []]))  # cursor now inside slot 1
    assert not document.at_top_level()
    assert not document.new_line()
    assert document.line_count() == 1


def test_undo_restores_line_structure() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))
    assert document.line_count() == 2
    assert document.undo()  # undo the "2"
    assert document.undo()  # undo the new line
    assert document.line_count() == 1


# --- rendering --------------------------------------------------------------


def test_render_joins_lines_with_newlines() -> None:
    document = Document()
    document.lines = [[Character("1"), Sign("plus")], [Character("2")]]
    text, _ = presenter().render(document)
    assert text == "1+\n2"


def test_cursor_offset_counts_previous_lines() -> None:
    document = Document()
    document.insert(Character("1"))
    document.new_line()
    document.insert(Character("2"))  # cursor after 2, on line 1
    text, position = presenter().render(document)
    assert text == "1\n2"
    assert position == 3  # "1" + "\n" + "2"


# --- through the editor -----------------------------------------------------


def test_return_makes_a_new_line_and_reads_it() -> None:
    editor = create_editor(DATA, language="en")
    editor.type_character("1")
    result = editor.press("Return")
    assert result is not None
    assert result.speech == "new line"
    assert result.text == "1\n"
    editor.type_character("2")
    line = editor.press("Ctrl+Shift+L")  # reads the current line only
    assert line is not None
    assert line.speech == "2"


@pytest.mark.parametrize("language", ["en", "es"])
def test_calculate_operates_on_the_current_line(language: str) -> None:
    editor = create_editor(DATA, language=language)
    for stroke in ["1", "+", "1"]:
        editor.type_character(stroke) if stroke.isdigit() else editor.press(stroke)
    editor.press("Return")
    for stroke in ["2", "+", "3"]:
        editor.type_character(stroke) if stroke.isdigit() else editor.press(stroke)
    result = editor.press("Ctrl+Return")  # current line is "2+3"
    assert result is not None
    assert result.speech.endswith("5")
