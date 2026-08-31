"""Validation of the common envelope and of the table models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from disvimat.core.elements import Element, ElementType, Record
from disvimat.core.tables import (
    BrailleEntry,
    Catalog,
    GlyphEntry,
    KeyEntry,
    LabelEntry,
    MessageEntry,
    PlatformKeyEntry,
    Table,
    data_dir,
    load_table,
)

DATA = Path(__file__).resolve().parents[1] / "data"


def test_data_dir_points_at_the_project() -> None:
    assert data_dir() == DATA


def test_catalog_loads() -> None:
    catalog = Catalog.load(DATA / "elements.json")
    assert len(catalog) > 0
    assert "fraction" in catalog
    assert catalog["fraction"].type is ElementType.STRUCTURE
    assert catalog["fraction"].arity == 2


@pytest.mark.parametrize(
    ("filename", "entry_type"),
    [
        ("keys_signs.json", KeyEntry),
        ("keys_commands.json", KeyEntry),
        ("keys_numpad.json", KeyEntry),
        ("keys_platform.json", PlatformKeyEntry),
        ("glyphs.json", GlyphEntry),
        ("labels.en.json", LabelEntry),
        ("labels.es.json", LabelEntry),
        ("labels.fr.json", LabelEntry),
        ("messages.en.json", MessageEntry),
        ("messages.es.json", MessageEntry),
        ("messages.fr.json", MessageEntry),
        ("ui.en.json", MessageEntry),
        ("ui.es.json", MessageEntry),
        ("ui.fr.json", MessageEntry),
        ("br6.es.json", BrailleEntry),
    ],
)
def test_tables_load(filename: str, entry_type: type[Record]) -> None:
    table = load_table(DATA / filename, entry_type)
    assert table.entries


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        Table[GlyphEntry](
            table="glyphs",
            version=1,
            entries=[GlyphEntry(id="plus", glyph="+"), GlyphEntry(id="plus", glyph="-")],
        )


def test_structure_without_arity_is_rejected() -> None:
    with pytest.raises(ValidationError, match="arity"):
        Element(id="x", type=ElementType.STRUCTURE, category="algebra")


def test_sign_with_arity_is_rejected() -> None:
    with pytest.raises(ValidationError, match="arity"):
        Element(id="x", type=ElementType.SIGN, category="arithmetic", arity=2)


def test_unknown_parts_are_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown parts"):
        LabelEntry(id="x", label="x", parts={"middle": "y"})


def test_braille_entry_needs_cells_or_parts() -> None:
    with pytest.raises(ValidationError, match="cells or parts"):
        BrailleEntry(id="x")
