"""Filter A1 and export C1: round trip MathML <-> DisvimatEditor tree."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from disvimat.core.document import Character, Node, Sign, Structure
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.tables import Catalog
from disvimat.export.xhtml import XHTMLExporter

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


def test_round_trip(catalog: Catalog) -> None:
    nodes: list[Node] = [
        Character("1"),
        Character("2"),
        Sign("plus"),
        Structure(
            "fraction",
            [[Character("3")], [Character("4"), Sign("minus"), Character("5")]],
        ),
    ]
    text = ET.tostring(XHTMLExporter(catalog).mathml(nodes), encoding="unicode")
    assert MathMLFilter(catalog).from_text(text) == nodes


def test_round_trip_of_root_and_power(catalog: Catalog) -> None:
    nodes: list[Node] = [
        Structure("sqrt", [[Character("x")]]),
        Sign("plus"),
        Structure("power", [[Character("x")], [Character("2")]]),
    ]
    text = ET.tostring(XHTMLExporter(catalog).mathml(nodes), encoding="unicode")
    assert MathMLFilter(catalog).from_text(text) == nodes


def test_empty_slots_survive(catalog: Catalog) -> None:
    nodes: list[Node] = [Structure("fraction", [[], []])]
    text = ET.tostring(XHTMLExporter(catalog).mathml(nodes), encoding="unicode")
    assert MathMLFilter(catalog).from_text(text) == nodes


def test_digits_are_grouped_into_mn(catalog: Catalog) -> None:
    nodes: list[Node] = [Character("1"), Character("2"), Character("3")]
    math = XHTMLExporter(catalog).mathml(nodes)
    assert [(child.tag, child.text) for child in math] == [("mn", "123")]


def test_imports_namespaced_mathml(catalog: Catalog) -> None:
    text = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>7</mn><mo>+</mo><mn>1</mn></math>'
    nodes = MathMLFilter(catalog).from_text(text)
    assert nodes == [Character("7"), Sign("plus"), Character("1")]


def test_unknown_sign_gives_a_clear_error(catalog: Catalog) -> None:
    with pytest.raises(FilterError, match="no DisvimatEditor correspondence"):
        MathMLFilter(catalog).from_text("<math><mo>∮</mo></math>")


def test_xhtml_without_math_gives_a_clear_error(catalog: Catalog) -> None:
    with pytest.raises(FilterError, match="no <math> expression"):
        MathMLFilter(catalog).from_xhtml("<html><body><p>no maths</p></body></html>")


def test_complete_xhtml_document(catalog: Catalog) -> None:
    document = XHTMLExporter(catalog).xhtml_document([Character("1")], title="Test")
    assert "<title>Test</title>" in document
    assert "<math" in document and "<mn>1</mn>" in document
