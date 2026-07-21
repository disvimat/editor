"""The DisvimatEditor element model (prior decision "a" of the README).

An element is the smallest unit the editor operates on: a sign (no
slots), a structure (with slots, e.g. a fraction) or a command (an
editor action). The in-memory document is a tree whose nodes reference
these elements by their ``id``.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Element ids are ASCII, lowercase and immutable: every other table
#: (keys, glyphs, labels, braille...) refers to them.
ID_PATTERN = r"^[a-z][a-z0-9_]*$"

#: Catalogue element standing for an empty slot (presentation and speech).
#: It is not editable and has no key assigned.
SLOT_ID = "slot"


class Record(BaseModel):
    """Base of every table record: a stable reference through ``id``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)


class ElementType(StrEnum):
    """Basic typing of DisvimatEditor elements."""

    SIGN = "sign"
    STRUCTURE = "structure"
    COMMAND = "command"


class Element(Record):
    """An entry of the DisvimatEditor catalogue.

    ``mathml`` and ``unicode`` hold the correspondence with XHTML (filter
    A1); ``arity`` is the number of slots of a structure; ``level`` is the
    lowest user level the element is available at (profiles, A7).
    """

    type: ElementType
    category: str
    mathml: str | None = None
    unicode: str | None = None
    arity: int = Field(default=0, ge=0)
    level: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _consistent_arity(self) -> Self:
        if self.type is ElementType.STRUCTURE and self.arity < 1:
            raise ValueError(f"structure {self.id!r} must have arity >= 1")
        if self.type is not ElementType.STRUCTURE and self.arity != 0:
            raise ValueError(f"{self.id!r} is not a structure: its arity must be 0")
        return self
