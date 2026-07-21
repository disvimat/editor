"""Export C1: DisvimatEditor tree -> MathML / XHTML document.

This is the inverse of filter A1: signs come out as ``<mo>`` with their
catalogue ``unicode``, structures as their ``mathml`` element, and digits
and letters are grouped into ``<mn>`` and ``<mi>``.
"""

import xml.etree.ElementTree as ET

from disvimat.core.document import Character, Node, Sign, Structure
from disvimat.core.tables import Catalog

MATHML_NS = "http://www.w3.org/1998/Math/MathML"

_XHTML_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{language}" xml:lang="{language}">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
</head>
<body>
<p>{mathml}</p>
</body>
</html>
"""


class XHTMLExporter:
    """Builds MathML and XHTML documents from the editor tree."""

    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def mathml(self, nodes: list[Node]) -> ET.Element:
        """A ``<math>`` element holding the content of the sequence."""
        math = ET.Element("math", {"xmlns": MATHML_NS, "display": "block"})
        self._fill(math, nodes)
        return math

    def xhtml_document(
        self, nodes: list[Node], title: str = "DISVIMAT document", language: str = "en"
    ) -> str:
        """A complete XHTML document with the expression as MathML."""
        math_text = ET.tostring(self.mathml(nodes), encoding="unicode")
        return _XHTML_TEMPLATE.format(title=title, language=language, mathml=math_text)

    # --- internals ------------------------------------------------------------

    def _fill(self, parent: ET.Element, nodes: list[Node]) -> None:
        index = 0
        while index < len(nodes):
            node = nodes[index]
            if isinstance(node, Character):
                index = self._characters(parent, nodes, index)
                continue
            if isinstance(node, Sign):
                symbol = self._catalog[node.element_id].unicode
                if symbol is None:
                    raise ValueError(f"sign {node.element_id!r} has no unicode")
                ET.SubElement(parent, "mo").text = symbol
            else:
                self._structure(parent, node)
            index += 1

    def _characters(self, parent: ET.Element, nodes: list[Node], index: int) -> int:
        """Group consecutive digits into ``<mn>``; letters go into ``<mi>``."""
        node = nodes[index]
        assert isinstance(node, Character)
        if node.text.isdigit():
            end = index
            while (
                end < len(nodes) and isinstance(nodes[end], Character) and nodes[end].text.isdigit()  # type: ignore[union-attr]
            ):
                end += 1
            digits = "".join(n.text for n in nodes[index:end] if isinstance(n, Character))
            ET.SubElement(parent, "mn").text = digits
            return end
        ET.SubElement(parent, "mi").text = node.text
        return index + 1

    def _structure(self, parent: ET.Element, structure: Structure) -> None:
        element = self._catalog[structure.element_id]
        if element.mathml is None:
            raise ValueError(f"structure {structure.element_id!r} has no MathML correspondence")
        container = ET.SubElement(parent, element.mathml)
        if element.mathml == "msqrt":
            # msqrt carries no slot wrapper: the content goes straight in
            self._fill(container, structure.slots[0])
            return
        for slot in structure.slots:
            self._slot(container, slot)

    def _slot(self, parent: ET.Element, nodes: list[Node]) -> None:
        """A slot is a single child: wrapped in ``<mrow>`` when needed."""
        temporary = ET.Element("temporary")
        self._fill(temporary, nodes)
        children = list(temporary)
        if len(children) == 1:
            parent.append(children[0])
        else:
            mrow = ET.SubElement(parent, "mrow")
            mrow.extend(children)
