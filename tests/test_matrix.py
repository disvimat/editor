"""Two-dimensional structures — matrices (modules A10 / B7).

A matrix is a grid of cells. It reuses the cursor machinery (a cell is a
slot addressed row-major), and adds grid navigation and growth. These tests
pin the model, the linear rendering, the reading, the MathML round trip and
the .dvm round trip.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from disvimat.core.document import Character, Document, Matrix, Node, Sign
from disvimat.core.dvm import from_dvm, to_dvm
from disvimat.core.editor import create_editor
from disvimat.core.filters.mathml import MathMLFilter
from disvimat.core.presentation import Presenter
from disvimat.core.speech import Speaker
from disvimat.core.tables import Catalog, GlyphEntry, LabelEntry, load_table
from disvimat.export.xhtml import XHTMLExporter

DATA = Path(__file__).resolve().parents[1] / "data"


def matrix_2x2() -> Matrix:
    return Matrix(
        "matrix",
        rows=2,
        cols=2,
        slots=[[Character("1")], [Character("2")], [Character("3")], [Character("4")]],
    )


# --- the document model -----------------------------------------------------


def test_insert_matrix_enters_the_first_cell() -> None:
    document = Document()
    document.insert(Matrix("matrix", rows=2, cols=2, slots=[[], [], [], []]))
    assert document.current_matrix() is not None
    assert document.cursor_cell() == (0, 0)


def test_tab_walks_cells_row_major() -> None:
    document = Document()
    document.insert(Matrix("matrix", rows=2, cols=2, slots=[[], [], [], []]))
    document.insert(Character("a"))
    document.next_slot()  # -> cell (0,1)
    assert document.cursor_cell() == (0, 1)
    document.next_slot()  # -> (1,0)
    assert document.cursor_cell() == (1, 0)


def test_grid_navigation() -> None:
    document = Document()
    document.insert(matrix_2x2())  # cursor in cell (0,0)
    assert document.move_in_matrix(1, 0) == (1, 0)  # down
    assert document.move_in_matrix(0, 1) == (1, 1)  # right
    assert document.move_in_matrix(-1, 0) == (0, 1)  # up
    assert document.move_in_matrix(0, -1) == (0, 0)  # left
    assert document.move_in_matrix(-1, 0) is None  # off the top edge


def test_add_row_and_column() -> None:
    document = Document()
    document.insert(matrix_2x2())
    assert document.matrix_add_row()
    matrix = document.current_matrix()
    assert matrix is not None
    assert (matrix.rows, matrix.cols) == (3, 2)
    assert document.matrix_add_column()
    matrix = document.current_matrix()
    assert matrix is not None
    assert (matrix.rows, matrix.cols) == (3, 3)
    assert len(matrix.slots) == 9


def test_growing_a_matrix_is_undoable() -> None:
    document = Document()
    document.insert(matrix_2x2())
    document.matrix_add_row()
    assert document.undo()
    matrix = document.current_matrix()
    assert matrix is not None
    assert matrix.rows == 2


# --- presentation and speech ------------------------------------------------


def test_linear_rendering() -> None:
    presenter = Presenter(load_table(DATA / "glyphs.json", GlyphEntry))
    document = Document()
    document.lines = [[matrix_2x2()]]
    text, _ = presenter.render(document)
    assert text == "[1,2;3,4]"


def test_empty_cells_show_the_slot_glyph() -> None:
    presenter = Presenter(load_table(DATA / "glyphs.json", GlyphEntry))
    document = Document()
    document.lines = [[Matrix("matrix", rows=1, cols=2, slots=[[Character("1")], []])]]
    text, _ = presenter.render(document)
    assert text == "[1,□]"


def test_reading_row_by_row() -> None:
    speaker = Speaker(load_table(DATA / "labels.es.json", LabelEntry))
    assert speaker.node(matrix_2x2()) == "matriz 1 2 siguiente fila 3 4 fin de matriz"


# --- MathML and .dvm round trips --------------------------------------------


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


def test_mathml_round_trip(catalog: Catalog) -> None:
    nodes: list[Node] = [matrix_2x2()]
    text = ET.tostring(XHTMLExporter(catalog).mathml(nodes), encoding="unicode")
    assert "<mtable>" in text and "<mtr>" in text and "<mtd>" in text
    assert MathMLFilter(catalog).from_text(text) == nodes


def test_mathml_matrix_inside_an_expression(catalog: Catalog) -> None:
    nodes: list[Node] = [Character("2"), Sign("times"), matrix_2x2()]
    text = ET.tostring(XHTMLExporter(catalog).mathml(nodes), encoding="unicode")
    assert MathMLFilter(catalog).from_text(text) == nodes


def test_dvm_round_trip() -> None:
    lines = [[matrix_2x2()]]
    assert from_dvm(to_dvm(lines, language="es")).lines == lines


# --- through the editor -----------------------------------------------------


def test_editor_inserts_and_reads_a_matrix() -> None:
    editor = create_editor(DATA, language="en", addons=False)
    result = editor.press("Ctrl+Shift+M")
    assert result is not None
    assert result.text == "[□,□;□,□]"
    assert result.speech.startswith("matrix")

    for stroke in ["1", "Tab", "2", "Tab", "3", "Tab", "4"]:
        editor.type_character(stroke) if stroke.isdigit() else editor.press(stroke)
    line = editor.press("Ctrl+Shift+L")
    assert line is not None
    assert line.text == "[1,2;3,4]"
    assert line.speech == "matrix 1 2 next row 3 4 end of matrix"


def test_editor_grows_a_matrix() -> None:
    editor = create_editor(DATA, language="en", addons=False)
    editor.press("Ctrl+Shift+M")
    editor.type_character("1")
    editor.press("Alt+Down")  # add row
    editor.press("Alt+Right")  # add column
    line = editor.press("Ctrl+Shift+L")
    assert line is not None
    assert line.text == "[1,□,□;□,□,□;□,□,□]"


def test_a_matrix_is_not_computable() -> None:
    editor = create_editor(DATA, language="en", addons=False)
    editor.press("Ctrl+Shift+M")
    editor.press("Ctrl+Shift+L")  # move out is not needed; calculate the line
    result = editor.press("Ctrl+Return")
    assert result is not None
    assert result.speech == "the expression cannot be computed"
