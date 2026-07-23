"""Filter A1: MathML (XHTML) -> DisvimatEditor tree.

The correspondence comes from the catalogue: ``<mo>`` elements resolve
through the ``unicode`` field of the signs, and structure elements
(``mfrac``, ``msup``...) through the ``mathml`` field. Content without a
correspondence raises :class:`FilterError` with a clear message (the
README's "provision for new signs" is still to come).
"""

import xml.etree.ElementTree as ET

from disvimat.core.document import Character, Matrix, Node, Sign, Structure
from disvimat.core.elements import ElementType
from disvimat.core.tables import Catalog

#: Catalogue id of the matrix element (the insert command / node id).
MATRIX_ID = "matrix"


class FilterError(ValueError):
    """The MathML holds something with no DisvimatEditor correspondence."""


def _local_name(element: ET.Element) -> str:
    """Name of the element without the MathML namespace."""
    return element.tag.rpartition("}")[2]


class MathMLFilter:
    """Converts MathML expressions into sequences of DisvimatEditor nodes."""

    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog
        self._signs_by_unicode = {
            element.unicode: element.id
            for element in catalog.by_type(ElementType.SIGN)
            if element.unicode
        }
        self._structures_by_mathml = {
            element.mathml: element
            for element in catalog.by_type(ElementType.STRUCTURE)
            if element.mathml
        }

    def from_text(self, xml_text: str) -> list[Node]:
        """Convert a ``<math>...</math>`` fragment into nodes."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as error:
            raise FilterError(f"malformed MathML: {error}") from error
        return self._sequence(root)

    def from_xhtml(self, xhtml_text: str) -> list[Node]:
        """Extract the first ``<math>`` expression of an XHTML document (D1)."""
        try:
            root = ET.fromstring(xhtml_text)
        except ET.ParseError as error:
            raise FilterError(f"malformed XHTML: {error}") from error
        for element in root.iter():
            if _local_name(element) == "math":
                return self._sequence(element)
        raise FilterError("the document holds no <math> expression")

    # --- internals ------------------------------------------------------------

    def _sequence(self, container: ET.Element) -> list[Node]:
        nodes: list[Node] = []
        for child in container:
            nodes.extend(self._nodes(child))
        return nodes

    def _nodes(self, element: ET.Element) -> list[Node]:
        name = _local_name(element)
        if name == "mrow":
            return self._sequence(element)
        if name in ("mn", "mi", "mtext"):
            return [Character(character) for character in (element.text or "").strip()]
        if name == "mo":
            text = (element.text or "").strip()
            sign_id = self._signs_by_unicode.get(text)
            if sign_id is None:
                raise FilterError(f"sign with no DisvimatEditor correspondence: {text!r}")
            return [Sign(sign_id)]
        if name == "msqrt":
            # msqrt has no slot wrapper: its children are the content
            return [self._structure(name, [self._sequence(element)])]
        if name in ("mtable", "mtr"):
            return [self._matrix(element)]
        catalog_element = self._structures_by_mathml.get(name)
        if catalog_element is None:
            raise FilterError(f"MathML element with no correspondence: <{name}>")
        children = list(element)
        if len(children) != catalog_element.arity:
            raise FilterError(
                f"<{name}> has {len(children)} children but {catalog_element.arity} were expected"
            )
        return [self._structure(name, [self._nodes(child) for child in children])]

    def _matrix(self, table: ET.Element) -> Matrix:
        """Read a ``<mtable>`` (rows of ``<mtd>``) into a Matrix node."""
        rows = [row for row in table if _local_name(row) == "mtr"]
        cells: list[list[Node]] = []
        cols = 0
        for row in rows:
            row_cells = [self._sequence(cell) for cell in row if _local_name(cell) == "mtd"]
            cols = max(cols, len(row_cells))
            cells.extend(row_cells)
        # Pad short rows so the grid is rectangular.
        if rows and cols:
            padded: list[list[Node]] = []
            index = 0
            for row in rows:
                width = sum(1 for cell in row if _local_name(cell) == "mtd")
                padded.extend(cells[index : index + width])
                padded.extend([[] for _ in range(cols - width)])
                index += width
            cells = padded
        return Matrix(MATRIX_ID, rows=len(rows), cols=cols, slots=cells)

    def _structure(self, mathml_name: str, slots: list[list[Node]]) -> Structure:
        element = self._structures_by_mathml.get(mathml_name)
        if element is None:
            raise FilterError(f"MathML element with no correspondence: <{mathml_name}>")
        return Structure(element.id, slots)
