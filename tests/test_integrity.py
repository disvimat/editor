"""Consistency between the data/ tables (principle 5 of the plan).

When one of these tests fails the tables must be fixed, not the tests:
they are the contract keeping an inconsistent table away from the user.
"""

from pathlib import Path

import pytest

from disvimat.core.elements import ElementType
from disvimat.core.integrity import key_conflicts, uncovered_ids, unknown_ids
from disvimat.core.tables import (
    BrailleEntry,
    Catalog,
    GlyphEntry,
    KeyEntry,
    LabelEntry,
    MessageEntry,
    Table,
    load_table,
)

DATA = Path(__file__).resolve().parents[1] / "data"

#: Languages that must offer a full set of speech/message/interface tables.
LANGUAGES = ["en", "es", "fr"]


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


@pytest.fixture(scope="module")
def keys_signs() -> Table[KeyEntry]:
    return load_table(DATA / "keys_signs.json", KeyEntry)


@pytest.fixture(scope="module")
def keys_commands() -> Table[KeyEntry]:
    return load_table(DATA / "keys_commands.json", KeyEntry)


def test_every_table_references_known_ids(catalog: Catalog) -> None:
    tables: list[tuple[str, type]] = [
        ("keys_signs.json", KeyEntry),
        ("keys_commands.json", KeyEntry),
        ("keys_numpad.json", KeyEntry),
        ("glyphs.json", GlyphEntry),
        ("br6.es.json", BrailleEntry),
        *[(f"labels.{language}.json", LabelEntry) for language in LANGUAGES],
    ]
    for filename, entry_type in tables:
        table = load_table(DATA / filename, entry_type)
        assert unknown_ids(table, catalog) == set(), filename


def test_glyphs_cover_signs_and_structures(catalog: Catalog) -> None:
    table = load_table(DATA / "glyphs.json", GlyphEntry)
    types = {ElementType.SIGN, ElementType.STRUCTURE}
    assert uncovered_ids(table, catalog, types) == set()


@pytest.mark.parametrize("language", LANGUAGES)
def test_labels_cover_every_element(catalog: Catalog, language: str) -> None:
    table = load_table(DATA / f"labels.{language}.json", LabelEntry)
    assert uncovered_ids(table, catalog, set(ElementType)) == set()


def test_br6_covers_signs_and_structures(catalog: Catalog) -> None:
    table = load_table(DATA / "br6.es.json", BrailleEntry)
    types = {ElementType.SIGN, ElementType.STRUCTURE}
    assert uncovered_ids(table, catalog, types) == set()


@pytest.mark.parametrize("name", ["messages", "ui"])
def test_translations_have_the_same_ids(name: str) -> None:
    """Every language must define exactly the same message/interface ids."""
    reference = {entry.id for entry in load_table(DATA / f"{name}.en.json", MessageEntry).entries}
    for language in LANGUAGES:
        table = load_table(DATA / f"{name}.{language}.json", MessageEntry)
        assert {entry.id for entry in table.entries} == reference, f"{name}.{language}"


def test_keys_signs_never_reference_commands(catalog: Catalog, keys_signs: Table[KeyEntry]) -> None:
    for entry in keys_signs.entries:
        assert catalog[entry.id].type is not ElementType.COMMAND, entry.id


def test_keys_commands_only_reference_commands(
    catalog: Catalog, keys_commands: Table[KeyEntry]
) -> None:
    for entry in keys_commands.entries:
        assert catalog[entry.id].type is ElementType.COMMAND, entry.id


def test_no_key_stroke_conflicts(
    keys_signs: Table[KeyEntry], keys_commands: Table[KeyEntry]
) -> None:
    keys_numpad = load_table(DATA / "keys_numpad.json", KeyEntry)
    assert key_conflicts(keys_signs, keys_commands, keys_numpad) == {}
