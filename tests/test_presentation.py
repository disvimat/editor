"""Linear rendering with glyphs, templates and cursor position."""

from pathlib import Path

from disvimat.core.document import Character, Document, Sign, Structure
from disvimat.core.presentation import Presenter
from disvimat.core.tables import GlyphEntry, Table, load_table

DATA = Path(__file__).resolve().parents[1] / "data"


def presenter() -> Presenter:
    return Presenter(load_table(DATA / "glyphs.json", GlyphEntry))


def test_empty_document() -> None:
    assert presenter().render(Document()) == ("", 0)


def test_linear_rendering_with_template() -> None:
    document = Document()
    document.lines = [
        [
            Character("1"),
            Sign("plus"),
            Structure("fraction", [[Character("2")], [Character("3")]]),
        ]
    ]
    text, position = presenter().render(document)
    assert text == "1+(2∕3)"
    assert position == 0  # cursor at the start


def test_empty_slot_uses_the_slot_glyph() -> None:
    document = Document()
    document.lines = [[Structure("fraction", [[Character("2")], []])]]
    text, _ = presenter().render(document)
    assert text == "(2∕□)"


def test_cursor_inside_an_empty_slot() -> None:
    document = Document()
    document.insert(Character("1"))
    document.insert(Sign("plus"))
    document.insert(Structure("fraction", [[], []]))
    text, position = presenter().render(document)
    assert text == "1+(□∕□)"
    assert position == text.index("□")


def test_structure_without_template_uses_the_generic_form() -> None:
    table = Table[GlyphEntry](
        table="glyphs",
        version=1,
        entries=[GlyphEntry(id="slot", glyph="□"), GlyphEntry(id="box", glyph="◧")],
    )
    document = Document()
    document.lines = [[Structure("box", [[Character("1")], []])]]
    text, _ = Presenter(table).render(document)
    assert text == "◧(1;□)"
