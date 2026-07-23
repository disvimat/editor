"""Loading and validation of the DisvimatEditor tables (prior decision "b").

Every table shares the same JSON envelope::

    {"table": "...", "version": 1, "language": "es" | null, "entries": [...]}

and is validated with pydantic on load: an inconsistent table fails here,
with a clear message for the maintainer, and never reaches the end user.

Conventions:

- Key strokes (``keys``) use the canonical English names emitted by wx and
  by the browser ("Left", "Ctrl+F", "Ctrl+Shift+R"); they are never
  translated. User-visible labels are localised in their own table.
- Language-dependent tables carry a suffix: ``labels.es.json``.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from disvimat.core.elements import Element, ElementType, Record

#: Reference language: every language-dependent table falls back to it.
FALLBACK_LANGUAGE = "en"


class KeyEntry(Record):
    """A2/A3/A4: element -> key stroke (with conditions)."""

    keys: str
    condition: str | None = None


class GlyphEntry(Record):
    """B1: glyph used to present a sign or structure in linear editing.

    Structures may carry a linear ``template`` with ``{1}``, ``{2}``...
    marks for their slots: ``"({1}∕{2})"`` for the fraction. Without a
    template the presentation is generic: ``glyph(s1;s2)``.
    """

    glyph: str
    template: str | None = None


#: Parts allowed in the linear speech of a structure.
VALID_PARTS = frozenset({"start", "separator", "end"})


class LabelEntry(Record):
    """B2: text label for lists, the status line and speech synthesis.

    Structures may carry ``parts`` (start/separator/end) for linear
    reading: "fraction ... over ... end of fraction".
    """

    label: str
    parts: dict[str, str] | None = None

    @field_validator("parts")
    @classmethod
    def _known_parts(cls, parts: dict[str, str] | None) -> dict[str, str] | None:
        if parts:
            unknown = set(parts) - VALID_PARTS
            if unknown:
                raise ValueError(f"unknown parts: {sorted(unknown)}")
        return parts


class BrailleEntry(Record):
    """B3/B5: correspondence of an element with braille cells.

    A cell is written with its dots ("1-4-5"; "" is the blank cell).
    Signs carry ``cells``; structures carry ``parts``
    (start/separator/end), each with its own list of cells.
    """

    cells: list[str] | None = None
    parts: dict[str, list[str]] | None = None

    @field_validator("parts")
    @classmethod
    def _known_parts(cls, parts: dict[str, list[str]] | None) -> dict[str, list[str]] | None:
        if parts:
            unknown = set(parts) - VALID_PARTS
            if unknown:
                raise ValueError(f"unknown parts: {sorted(unknown)}")
        return parts

    @model_validator(mode="after")
    def _something_to_transcribe(self) -> Self:
        if self.cells is None and self.parts is None:
            raise ValueError(f"{self.id!r} needs cells or parts")
        return self


class BrailleTextEntry(Record):
    """B5: correspondence of a text character (letter, digit) with cells.

    The ``id`` is descriptive ("letter_a", "digit_0", "space"); the actual
    lookup key is ``character``. Language-dependent table.
    """

    character: str = Field(min_length=1, max_length=1)
    cells: list[str] = Field(min_length=1)


class ProfileEntry(Record):
    """A7: user profile; limits the elements available by level.

    ``calculator`` implements the teacher's lock (A9): when false, the
    profile cannot use the calculator.
    """

    level: int = Field(ge=1)
    calculator: bool = True


class MessageEntry(Record):
    """Program messages for the user, localised per language.

    The core produces them identified by id (e.g. calculator errors); the
    text lives here, never in the code.
    """

    text: str


class Table[E: Record](BaseModel):
    """Common envelope of every DisvimatEditor table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    table: str
    version: int = Field(ge=1)
    language: str | None = None
    entries: list[E]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        seen: set[str] = set()
        for entry in self.entries:
            if entry.id in seen:
                raise ValueError(f"duplicate id in table {self.table!r}: {entry.id!r}")
            seen.add(entry.id)
        return self


def load_table[E: Record](path: Path, entry_type: type[E]) -> Table[E]:
    """Load and validate a JSON table with entries of the given type."""
    data = json.loads(path.read_text(encoding="utf-8"))
    model: type[Table[E]] = Table[entry_type]  # type: ignore[valid-type]
    return model.model_validate(data)


class Catalog:
    """Catalogue of DisvimatEditor elements with lookup by ``id``."""

    def __init__(self, elements: list[Element]) -> None:
        self._by_id: dict[str, Element] = {}
        for element in elements:
            if element.id in self._by_id:
                raise ValueError(f"duplicate id in the catalogue: {element.id!r}")
            self._by_id[element.id] = element

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load the catalogue from ``elements.json`` (same common envelope)."""
        return cls(load_table(path, Element).entries)

    def __contains__(self, element_id: str) -> bool:
        return element_id in self._by_id

    def __getitem__(self, element_id: str) -> Element:
        return self._by_id[element_id]

    def __iter__(self) -> Iterator[Element]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def ids(self) -> set[str]:
        return set(self._by_id)

    def by_type(self, element_type: ElementType) -> list[Element]:
        return [element for element in self if element.type is element_type]


def keymap_path(directory: Path, keymap: str) -> Path:
    """Path of a keyboard profile (``data/keymaps/<name>.json``).

    Keymaps let the editor answer to the same key strokes as another
    editor (Lambda, EDICO…), so a user can migrate without relearning.
    """
    return directory / "keymaps" / f"{keymap}.json"


def available_keymaps(directory: Path) -> list[str]:
    """The keyboard profiles shipped in the data directory, sorted."""
    folder = directory / "keymaps"
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.json"))


def language_table_path(directory: Path, name: str, language: str) -> Path:
    """Path of a language-dependent table, falling back to the reference one.

    Looks for ``name.<language>.json``; when it does not exist, returns the
    :data:`FALLBACK_LANGUAGE` version, so a missing translation degrades to
    the reference language instead of failing (E6).
    """
    path = directory / f"{name}.{language}.json"
    if path.exists():
        return path
    return directory / f"{name}.{FALLBACK_LANGUAGE}.json"


def data_dir() -> Path:
    """Table directory: ``$DISVIMAT_DATA`` or the project's ``data/``.

    Resolving relative to the code serves the editable development
    install; packaged applications should set the environment variable.
    """
    from_environment = os.environ.get("DISVIMAT_DATA")
    if from_environment:
        return Path(from_environment)
    return Path(__file__).resolve().parents[3] / "data"
