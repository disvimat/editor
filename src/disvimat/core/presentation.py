"""Linear presentation of the document with glyphs (B1 tables, B4 window).

Turns the tree into a string of text and computes the cursor offset
inside it, so the interface can place the caret. Empty slots are shown
with the glyph of the ``slot`` element.
"""

import re

from disvimat.core.document import (
    Character,
    Container,
    Document,
    Matrix,
    Node,
    Sign,
    Structure,
)
from disvimat.core.elements import SLOT_ID
from disvimat.core.tables import GlyphEntry, Table

_SLOT_MARK = re.compile(r"\{(\d+)\}")


class Presenter:
    """Linear rendering of the document according to the glyph table."""

    def __init__(self, glyphs: Table[GlyphEntry]) -> None:
        self._glyphs = {entry.id: entry.glyph for entry in glyphs.entries}
        self._templates = {entry.id: entry.template for entry in glyphs.entries if entry.template}

    def render(self, document: Document) -> tuple[str, int]:
        """The full multi-line text and the global cursor offset in it.

        Lines are joined with ``\\n``; the caret offset counts those
        separators so the interface can place it in a multi-line control.
        """
        rendered: list[str] = []
        position: int | None = None
        offset = 0
        for number, line in enumerate(document.lines):
            if number == document.cursor_line():
                text, inner = self._sequence(line, document.cursor_path(), document.cursor_index())
                assert inner is not None, "the cursor did not show up during rendering"
                position = offset + inner
            else:
                text = self.text(line)
            rendered.append(text)
            offset += len(text) + 1  # + 1 for the newline separator
        assert position is not None
        return "\n".join(rendered), position

    def glyph(self, element_id: str) -> str:
        return self._glyphs.get(element_id, "?")

    def text(self, nodes: list[Node]) -> str:
        """The linear text of a sequence without the cursor (for braille, etc.)."""
        return "".join(self._node(node) for node in nodes)

    # --- internals ----------------------------------------------------------

    def _sequence(
        self, nodes: list[Node], path: list[tuple[int, int]], index: int
    ) -> tuple[str, int | None]:
        """Render a sequence; the cursor is here when ``path`` is empty."""
        parts: list[str] = []
        position: int | None = None
        target_node = path[0][0] if path else None
        for i, node in enumerate(nodes):
            if not path and i == index:
                position = sum(map(len, parts))
            if i == target_node:
                assert isinstance(node, Container)
                text, inner = self._structure_with_cursor(node, path, index)
                if inner is not None:
                    position = sum(map(len, parts)) + inner
            else:
                text = self._node(node)
            parts.append(text)
        if not path and index == len(nodes):
            position = sum(map(len, parts))
        return "".join(parts), position

    def _structure_with_cursor(
        self, structure: Container, path: list[tuple[int, int]], index: int
    ) -> tuple[str, int | None]:
        target_slot = path[0][1]
        parts: list[str] = []
        position: int | None = None
        for piece in self._pieces(structure):
            if isinstance(piece, str):
                parts.append(piece)
                continue
            slot = structure.slots[piece]
            if piece == target_slot:
                if slot or path[1:]:
                    text, inner = self._sequence(slot, path[1:], index)
                else:
                    # empty slot holding the cursor: caret on the slot glyph
                    text, inner = self.glyph(SLOT_ID), 0
                if inner is not None:
                    position = sum(map(len, parts)) + inner
            else:
                text = self._slot(slot)
            parts.append(text)
        return "".join(parts), position

    def _node(self, node: Node) -> str:
        match node:
            case Character(text=text):
                return text
            case Sign(element_id=element_id):
                return self.glyph(element_id)
            case Structure() | Matrix():
                return "".join(
                    piece if isinstance(piece, str) else self._slot(node.slots[piece])
                    for piece in self._pieces(node)
                )

    def _slot(self, nodes: list[Node]) -> str:
        if not nodes:
            return self.glyph(SLOT_ID)
        return "".join(self._node(node) for node in nodes)

    def _pieces(self, container: Container) -> list[str | int]:
        """Literals and slot indices to render a container (cursor-agnostic)."""
        if isinstance(container, Matrix):
            return self._matrix_pieces(container)
        structure = container
        template = self._templates.get(structure.element_id)
        if template is None:
            inner = ";".join(f"{{{n + 1}}}" for n in range(len(structure.slots)))
            template = f"{self.glyph(structure.element_id)}({inner})"
        pieces: list[str | int] = []
        previous_end = 0
        for mark in _SLOT_MARK.finditer(template):
            if mark.start() > previous_end:
                pieces.append(template[previous_end : mark.start()])
            pieces.append(int(mark.group(1)) - 1)
            previous_end = mark.end()
        if previous_end < len(template):
            pieces.append(template[previous_end:])
        return pieces

    def _matrix_pieces(self, matrix: Matrix) -> list[str | int]:
        """Render a matrix as ``[a,b;c,d]``: comma between cells, ; between rows."""
        pieces: list[str | int] = ["["]
        for row in range(matrix.rows):
            if row > 0:
                pieces.append(";")
            for col in range(matrix.cols):
                if col > 0:
                    pieces.append(",")
                pieces.append(row * matrix.cols + col)
        pieces.append("]")
        return pieces
