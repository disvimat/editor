"""Speech rendering of the document with the B2 labels (voice, status line).

Structures are read linearly through their ``parts``:
"fraction, 1, over, 2, end of fraction". Adjacent characters are grouped
so the synthesiser reads "123" instead of "1, 2, 3".
"""

from disvimat.core.document import Character, Matrix, Node, Sign, Structure
from disvimat.core.elements import SLOT_ID
from disvimat.core.tables import LabelEntry, Table


class Speaker:
    """Textual reading of nodes and sequences from the label table."""

    def __init__(self, labels: Table[LabelEntry]) -> None:
        self._entries = {entry.id: entry for entry in labels.entries}

    def label(self, element_id: str) -> str:
        entry = self._entries.get(element_id)
        return entry.label if entry else element_id

    def node(self, node: Node) -> str:
        match node:
            case Character(text=text):
                return text
            case Sign(element_id=element_id):
                return self.label(element_id)
            case Structure():
                return self._structure(node)
            case Matrix():
                return self._matrix(node)

    def read(self, nodes: list[Node]) -> str:
        """Read a whole expression (the :class:`ExpressionReader` port)."""
        return self.sequence(nodes)

    def sequence(self, nodes: list[Node]) -> str:
        if not nodes:
            return self.label(SLOT_ID)
        parts: list[str] = []
        previous_was_character = False
        for node in nodes:
            if isinstance(node, Character) and previous_was_character:
                parts[-1] += node.text
            else:
                parts.append(self.node(node))
            previous_was_character = isinstance(node, Character)
        return " ".join(parts)

    def _structure(self, structure: Structure) -> str:
        entry = self._entries.get(structure.element_id)
        if entry is not None and entry.parts is not None:
            # with parts, the start is optional: "x to the power of 2"
            parts = entry.parts
            start = parts.get("start", "")
        else:
            parts = {}
            start = self.label(structure.element_id)
        separator = parts.get("separator", "")
        end = parts.get("end", "")
        pieces = [start] if start else []
        for number, slot in enumerate(structure.slots):
            if number > 0 and separator:
                pieces.append(separator)
            pieces.append(self.sequence(slot))
        if end:
            pieces.append(end)
        return " ".join(pieces)

    def _matrix(self, matrix: Matrix) -> str:
        """Read a matrix row by row: "matrix ... next row ... end of matrix"."""
        entry = self._entries.get(matrix.element_id)
        parts = entry.parts if entry and entry.parts else {}
        start = parts.get("start", self.label(matrix.element_id))
        row_separator = parts.get("separator", "")
        end = parts.get("end", "")
        pieces = [start] if start else []
        for row in range(matrix.rows):
            if row > 0 and row_separator:
                pieces.append(row_separator)
            for col in range(matrix.cols):
                pieces.append(self.sequence(matrix.cell(row, col)))
        if end:
            pieces.append(end)
        return " ".join(pieces)
