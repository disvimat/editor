"""Filter A1: MathML (XHTML) -> DisvimatEditor tree.

The correspondence comes from the catalogue: ``<mo>`` elements resolve
through the ``unicode`` field of the signs, and structure elements
(``mfrac``, ``msup``...) through the ``mathml`` field. Content without a
correspondence raises :class:`FilterError` with a clear message (the
README's "provision for new signs" is still to come).
"""

import xml.etree.ElementTree as ET
import xml.parsers.expat as expat

from disvimat.core.document import Character, Matrix, Node, Sign, Structure
from disvimat.core.elements import ElementType
from disvimat.core.tables import Catalog

#: Catalogue id of the matrix element (the insert command / node id).
MATRIX_ID = "matrix"


class FilterError(ValueError):
    """The MathML holds something with no DisvimatEditor correspondence."""


def _parse(xml_text: str, what: str) -> ET.Element:
    """Parse untrusted XML safely into a tree.

    Imported documents come from outside — a web request, or a file a
    desktop user was sent — so parsing them is a security boundary and we
    drive expat directly to control it. Two things are refused:

    - **Entity declarations.** A document can declare an entity that expands
      into another, ten times over, a few levels deep; a few hundred bytes
      then become gigabytes and exhaust the memory of whoever parses them
      (the "billion laughs" attack). Real MathML never declares entities.
    - **External entities**, which would make the parser fetch a local file
      or a URL of the attacker's choosing.

    A plain ``<!DOCTYPE html>`` without declarations keeps working, since
    that is what real XHTML documents carry.
    """
    builder = ET.TreeBuilder()
    # The separator makes expat report namespaced names as "uri}local"; the
    # opening brace is added back to reach ElementTree's "{uri}local" form.
    parser = expat.ParserCreate(namespace_separator="}")

    def qualified(name: str) -> str:
        return f"{{{name}" if "}" in name else name

    def start(name: str, attributes: dict[str, str]) -> None:
        builder.start(qualified(name), {qualified(k): v for k, v in attributes.items()})

    def end(name: str) -> None:
        builder.end(qualified(name))

    def refuse_entity(*_: object) -> None:
        raise FilterError("entity declarations are not allowed")

    def refuse_external(*_: object) -> bool:
        raise FilterError("external entities are not allowed")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = builder.data
    parser.EntityDeclHandler = refuse_entity
    parser.ExternalEntityRefHandler = refuse_external
    try:
        parser.Parse(xml_text, True)
    except expat.ExpatError as error:
        raise FilterError(f"malformed {what}: {error}") from error
    return builder.close()


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
        return self._sequence(_parse(xml_text, "MathML"))

    def from_xhtml(self, xhtml_text: str) -> list[Node]:
        """Extract the first ``<math>`` expression of an XHTML document (D1)."""
        root = _parse(xhtml_text, "XHTML")
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
