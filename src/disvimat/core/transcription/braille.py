"""Six-dot braille transcription driven by tables (module B5).

All braille knowledge lives in the per-language tables:
``br6.<language>.json`` (catalogue elements, with parts for structures)
and ``br6_text.<language>.json`` (letters and digits). The transcriber
only applies the general rules: the number prefix once per run of digits
and the capital prefix per uppercase letter.

Outputs: unicode braille (B6 window and braille displays) and ASCII
braille for the .BRA export (C3).

Unlike the other language-dependent tables, braille tables **do not fall
back** to another language: mathematical braille is normative and
differs per country (CBE in Spain, UEB in English, NMB in French), so
serving one language's braille to another would be plainly wrong. When
the table for a language is missing, :class:`BrailleTablesMissing` is
raised and the application disables its braille features.
"""

from pathlib import Path

from disvimat.core.document import Character, Matrix, Node, Sign, Structure
from disvimat.core.elements import SLOT_ID
from disvimat.core.tables import (
    BrailleEntry,
    BrailleTextEntry,
    Table,
    data_dir,
    load_table,
)

#: Service ids the br6 table must define (besides the catalogue elements).
NUMBER_PREFIX_ID = "number_prefix"
CAPITAL_ID = "capital"

#: North American braille ASCII (NABCC), indexed by the value of dots 1..6.
#: This is the provisional encoding of the .BRA export; once the CBE table
#: is available it is replaced here.
_ASCII_BRAILLE = " a1b'k2l@cif/msp\"e3h9o6r^djg>ntq,*5<-u8v.%[$+x!&;:4\\0z7(_?w]#y)="

#: Filler cell for anything without a transcription (all six dots).
_UNKNOWN_CELL = 0b111111


def unicode_to_ascii(braille: str) -> str:
    """Convert unicode braille (U+2800...) into ASCII braille.

    Shared with any external engine that returns unicode braille, so the
    ``.BRA`` export uses one single encoding whatever produced the cells.
    """
    return "".join(
        _ASCII_BRAILLE[ord(character) - 0x2800] if 0x2800 <= ord(character) <= 0x283F else character
        for character in braille
    )


class BrailleTablesMissing(FileNotFoundError):
    """There are no braille tables for the requested language."""

    def __init__(self, language: str) -> None:
        super().__init__(f"no braille tables for language {language!r}")
        self.language = language


def _cell(pattern: str) -> int:
    """Turn "1-4-5" into the dot mask; "" is the blank cell."""
    value = 0
    if pattern:
        for dot in pattern.split("-"):
            value |= 1 << (int(dot) - 1)
    return value


def _cells(patterns: list[str]) -> list[int]:
    return [_cell(pattern) for pattern in patterns]


class BrailleTranscriber:
    """Transcribes the document tree into braille according to the tables."""

    def __init__(self, elements: Table[BrailleEntry], text: Table[BrailleTextEntry]) -> None:
        self._by_element: dict[str, list[int]] = {}
        self._parts: dict[str, dict[str, list[int]]] = {}
        for entry in elements.entries:
            if entry.cells is not None:
                self._by_element[entry.id] = _cells(entry.cells)
            if entry.parts is not None:
                self._parts[entry.id] = {
                    part: _cells(patterns) for part, patterns in entry.parts.items()
                }
        self._by_character = {entry.character: _cells(entry.cells) for entry in text.entries}

    # --- outputs -------------------------------------------------------------

    def unicode(self, nodes: list[Node]) -> str:
        """Unicode braille (U+2800...) for the screen and braille displays."""
        return "".join(chr(0x2800 + cell) for cell in self.cells(nodes))

    def ascii(self, nodes: list[Node]) -> str:
        """ASCII braille for the .BRA export (C3)."""
        return "".join(_ASCII_BRAILLE[cell] for cell in self.cells(nodes))

    def cells(self, nodes: list[Node]) -> list[int]:
        """The cells (masks of dots 1..6) of the whole sequence."""
        result: list[int] = []
        self._sequence(nodes, result)
        return result

    # --- internals -------------------------------------------------------------

    def _sequence(self, nodes: list[Node], output: list[int]) -> None:
        in_number = False
        for node in nodes:
            if isinstance(node, Character):
                in_number = self._character(node.text, output, in_number)
                continue
            in_number = False
            if isinstance(node, Sign):
                output.extend(self._element(node.element_id))
            elif isinstance(node, Matrix):
                self._matrix(node, output)
            else:
                self._structure(node, output)

    def _character(self, character: str, output: list[int], in_number: bool) -> bool:
        if character.isdigit():
            if not in_number:
                output.extend(self._element(NUMBER_PREFIX_ID))
            output.extend(self._by_character.get(character, [_UNKNOWN_CELL]))
            return True
        if character.isupper() and character.lower() in self._by_character:
            output.extend(self._element(CAPITAL_ID))
            output.extend(self._by_character[character.lower()])
        else:
            output.extend(self._by_character.get(character, [_UNKNOWN_CELL]))
        return False

    def _structure(self, structure: Structure, output: list[int]) -> None:
        parts = self._parts.get(structure.element_id, {})
        output.extend(parts.get("start", []))
        for number, slot in enumerate(structure.slots):
            if number > 0:
                output.extend(parts.get("separator", []))
            if slot:
                self._sequence(slot, output)
            else:
                output.extend(self._element(SLOT_ID))
        output.extend(parts.get("end", []))

    def _matrix(self, matrix: Matrix, output: list[int]) -> None:
        """Best-effort table braille: cells in order, rows separated by a space.

        Proper mathematical matrix braille is normative and belongs to
        MathCAT; this is the fallback so a matrix still transcribes when the
        external engines are absent.
        """
        for row in range(matrix.rows):
            if row > 0:
                output.append(0)  # blank cell between rows
            for col in range(matrix.cols):
                if col > 0:
                    output.append(0)
                self._sequence(matrix.cell(row, col), output)

    def _element(self, element_id: str) -> list[int]:
        return self._by_element.get(element_id, [_UNKNOWN_CELL])


def braille_tables_available(directory: Path | None = None, language: str = "en") -> bool:
    """Whether both braille tables exist for the language (no fallback)."""
    directory = directory or data_dir()
    return (directory / f"br6.{language}.json").exists() and (
        directory / f"br6_text.{language}.json"
    ).exists()


def create_transcriber(directory: Path | None = None, language: str = "en") -> BrailleTranscriber:
    """Build the transcriber with the br6 tables of the given language.

    Raises :class:`BrailleTablesMissing` when the language has no tables:
    braille is never taken from a different language.
    """
    directory = directory or data_dir()
    if not braille_tables_available(directory, language):
        raise BrailleTablesMissing(language)
    elements: Table[BrailleEntry] = load_table(directory / f"br6.{language}.json", BrailleEntry)
    text: Table[BrailleTextEntry] = load_table(
        directory / f"br6_text.{language}.json", BrailleTextEntry
    )
    return BrailleTranscriber(elements, text)
