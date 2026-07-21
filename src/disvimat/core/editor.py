"""Editor controller: ties keyboard, document and presentations together.

The interfaces (desktop and web) are deliberately thin: they send
canonical key strokes or characters and reflect the :class:`Result`
(linear text, caret position and speech). All behaviour lives here and
in the ``data/`` tables.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.calculator import CalculationError, Calculator
from disvimat.core.document import Character, Document, Node, Sign, Structure
from disvimat.core.elements import SLOT_ID, ElementType
from disvimat.core.keyboard import Keyboard
from disvimat.core.output import ExpressionReader
from disvimat.core.presentation import Presenter
from disvimat.core.speech import Speaker
from disvimat.core.tables import (
    Catalog,
    GlyphEntry,
    KeyEntry,
    LabelEntry,
    MessageEntry,
    ProfileEntry,
    Table,
    data_dir,
    language_table_path,
    load_table,
)

#: Message id of the teacher's lock (A9); it lives in the messages table.
MSG_CALCULATOR_LOCKED = "calculator_locked"


@dataclass(frozen=True)
class Result:
    """What the interface must reflect after each action."""

    text: str
    position: int
    speech: str


class Editor:
    """The DisvimatEditor linear editor over an in-memory document."""

    def __init__(
        self,
        catalog: Catalog,
        keyboard: Keyboard,
        presenter: Presenter,
        speaker: Speaker,
        calculator: Calculator,
        messages: dict[str, str],
        *,
        calculator_allowed: bool = True,
        reader: ExpressionReader | None = None,
    ) -> None:
        self.catalog = catalog
        self.document = Document()
        self._keyboard = keyboard
        self._presenter = presenter
        self._speaker = speaker
        self._calculator = calculator
        self._messages = messages
        self._calculator_allowed = calculator_allowed
        # Reading a whole expression may come from an external engine
        # (MathCAT); the editing feedback always comes from the labels.
        self._reader: ExpressionReader = reader if reader is not None else speaker
        self._commands: dict[str, Callable[[], str]] = {
            "left": self._cmd_left,
            "right": self._cmd_right,
            "line_start": self._cmd_line_start,
            "line_end": self._cmd_line_end,
            "enter_structure": self._cmd_enter,
            "exit_structure": self._cmd_exit,
            "next_slot": self._cmd_next_slot,
            "delete": self._cmd_delete,
            "backspace": self._cmd_backspace,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "read_element": self._read_current,
            "read_line": self._cmd_read_line,
            "calculate": self._cmd_calculate,
        }

    # --- API for the interfaces ---------------------------------------------

    def press(self, keys: str) -> Result | None:
        """Run the key stroke from the tables; None when it is unassigned."""
        element = self._keyboard.resolve(keys)
        if element is None:
            return None
        if element.type is ElementType.COMMAND:
            command = self._commands.get(element.id)
            if command is None:
                return None
            return self._result(command())
        if element.type is ElementType.STRUCTURE:
            self.document.insert(Structure(element.id, [[] for _ in range(element.arity)]))
            label = self._speaker.label(element.id)
            return self._result(f"{label}, {self._speaker.label(SLOT_ID)} 1")
        self.document.insert(Sign(element.id))
        return self._result(self._speaker.label(element.id))

    def type_character(self, character: str) -> Result:
        """Insert a plain text character (digit, letter, space)."""
        self.document.insert(Character(character))
        return self._result(character)

    def state(self) -> Result:
        """The current state without running any action (line reading)."""
        return self._result(self._cmd_read_line())

    def load(self, nodes: list[Node]) -> Result:
        """Replace the document content (D imports); undoable."""
        self.document.load(nodes)
        return self._result(self._cmd_read_line())

    # --- commands ------------------------------------------------------------

    def _cmd_left(self) -> str:
        node = self.document.left()
        if node is None:
            return self._speaker.label("line_start")
        return self._speaker.node(node)

    def _cmd_right(self) -> str:
        node = self.document.right()
        if node is None:
            return self._speaker.label("line_end")
        return self._speaker.node(node)

    def _cmd_line_start(self) -> str:
        self.document.to_line_start()
        return self._speaker.label("line_start")

    def _cmd_line_end(self) -> str:
        self.document.to_line_end()
        return self._speaker.label("line_end")

    def _cmd_enter(self) -> str:
        structure = self.document.enter()
        if structure is None:
            return self._read_current()
        label = self._speaker.label("enter_structure")
        return f"{label}: {self._speaker.label(structure.element_id)}"

    def _cmd_exit(self) -> str:
        structure = self.document.exit()
        if structure is None:
            return self._read_current()
        label = self._speaker.label("exit_structure")
        return f"{label}: {self._speaker.label(structure.element_id)}"

    def _cmd_next_slot(self) -> str:
        structure = self.document.current_structure()
        if structure is None:
            return self._read_current()
        slot_number = self.document.next_slot()
        if slot_number is None:
            label = self._speaker.label("exit_structure")
            return f"{label}: {self._speaker.label(structure.element_id)}"
        return f"{self._speaker.label(SLOT_ID)} {slot_number + 1}"

    def _cmd_delete(self) -> str:
        node = self.document.delete()
        if node is None:
            return self._read_current()
        return f"{self._speaker.label('delete')}: {self._speaker.node(node)}"

    def _cmd_backspace(self) -> str:
        node = self.document.backspace()
        if node is None:
            return self._speaker.label("line_start")
        return f"{self._speaker.label('backspace')}: {self._speaker.node(node)}"

    def _cmd_undo(self) -> str:
        self.document.undo()
        return f"{self._speaker.label('undo')}: {self._cmd_read_line()}"

    def _cmd_redo(self) -> str:
        self.document.redo()
        return f"{self._speaker.label('redo')}: {self._cmd_read_line()}"

    def _cmd_calculate(self) -> str:
        """Compute the expression (A8), honouring the teacher's lock (A9)."""
        if not self._calculator_allowed:
            return self._message(MSG_CALCULATOR_LOCKED)
        try:
            value = self._calculator.evaluate(self.document.root)
        except CalculationError as error:
            return self._message(error.message_id)
        return f"{self._speaker.label('calculate')}: {value}"

    def _cmd_read_line(self) -> str:
        return self._reader.read(self.document.root)

    def _read_current(self) -> str:
        node = self.document.node_right()
        if node is None:
            return self._speaker.label("line_end")
        return self._speaker.node(node)

    def _message(self, message_id: str) -> str:
        return self._messages.get(message_id, message_id)

    def _result(self, speech: str) -> Result:
        text, position = self._presenter.render(self.document)
        return Result(text=text, position=position, speech=speech)


def create_editor(
    directory: Path | None = None,
    language: str = "en",
    profile: str | None = None,
    reader: ExpressionReader | None = None,
) -> Editor:
    """Build an editor loading every table from the data directory.

    ``language`` resolves the language-dependent tables (falling back to
    the reference language, E6); ``profile`` limits elements by level (A7);
    ``reader`` optionally replaces the table speaker when reading a whole
    expression (see :mod:`disvimat.backends`).
    """
    directory = directory or data_dir()
    catalog = Catalog.load(directory / "elements.json")
    level: int | None = None
    calculator_allowed = True
    if profile is not None:
        profiles: Table[ProfileEntry] = load_table(directory / "profiles.json", ProfileEntry)
        by_id = {entry.id: entry for entry in profiles.entries}
        if profile not in by_id:
            raise ValueError(f"unknown profile: {profile!r}")
        level = by_id[profile].level
        calculator_allowed = by_id[profile].calculator
    key_tables: list[Table[KeyEntry]] = [
        load_table(directory / name, KeyEntry)
        for name in ("keys_signs.json", "keys_commands.json", "keys_numpad.json")
    ]
    glyphs: Table[GlyphEntry] = load_table(directory / "glyphs.json", GlyphEntry)
    labels: Table[LabelEntry] = load_table(
        language_table_path(directory, "labels", language), LabelEntry
    )
    messages_table: Table[MessageEntry] = load_table(
        language_table_path(directory, "messages", language), MessageEntry
    )
    messages = {entry.id: entry.text for entry in messages_table.entries}
    return Editor(
        catalog,
        Keyboard(catalog, *key_tables, level=level),
        Presenter(glyphs),
        Speaker(labels),
        Calculator(),
        messages,
        calculator_allowed=calculator_allowed,
        reader=reader,
    )
