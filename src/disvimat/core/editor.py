"""Editor controller: ties keyboard, document and presentations together.

The interfaces (desktop and web) are deliberately thin: they send
canonical key strokes or characters and reflect the :class:`Result`
(linear text, caret position and speech). All behaviour lives here and
in the ``data/`` tables.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.addons import MSG_ADDON_FAILED, Registry, load_addons
from disvimat.core.calculator import CalculationError, Calculator
from disvimat.core.document import Character, Document, Matrix, Node, Sign, Structure
from disvimat.core.elements import SLOT_ID, Element, ElementType
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
    keymap_path,
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
        addons: Registry | None = None,
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
            "new_line": self._cmd_new_line,
            "delete": self._cmd_delete,
            "backspace": self._cmd_backspace,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "read_element": self._read_current,
            "read_line": self._cmd_read_line,
            "calculate": self._cmd_calculate,
            "matrix": self._cmd_matrix,
            "matrix_add_row": self._cmd_matrix_add_row,
            "matrix_add_column": self._cmd_matrix_add_column,
        }
        # Add-on commands join the same dispatch table, so they behave like
        # built-in ones — key resolution, speech and undo included.
        self.addons = addons if addons is not None else Registry()
        for command in self.addons.commands.values():
            self._commands[command.id] = self._addon_runner(command.run)

    def _addon_runner(self, run: Callable[["Editor"], str]) -> Callable[[], str]:
        """Wrap an add-on command so a failure cannot break the editor."""

        def call() -> str:
            try:
                return run(self)
            except Exception:  # noqa: BLE001 - contained on purpose
                return self._message(MSG_ADDON_FAILED)

        return call

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
        """Replace the document content with a single line (imports); undoable."""
        self.document.load(nodes)
        return self._result(self._cmd_read_line())

    def load_lines(self, lines: list[list[Node]]) -> Result:
        """Replace the document with several lines (open .dvm); undoable."""
        self.document.load_lines(lines)
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
        # Inside a matrix, Down moves to the cell below.
        if self.document.current_matrix() is not None:
            if self.document.move_in_matrix(1, 0) is not None:
                return self._announce_cell()
            return self._read_current()
        container = self.document.enter()
        if container is not None:
            label = self._speaker.label("enter_structure")
            return f"{label}: {self._speaker.label(container.element_id)}"
        # At the top level, Down moves to the next document line.
        if self.document.line_down():
            return self._cmd_read_line()
        return self._read_current()

    def _cmd_exit(self) -> str:
        # Inside a matrix, Up moves to the cell above; from the top row it
        # leaves the matrix.
        if self.document.current_matrix() is not None:
            if self.document.move_in_matrix(-1, 0) is not None:
                return self._announce_cell()
            self.document.exit()
            return self._read_current()
        container = self.document.exit()
        if container is not None:
            label = self._speaker.label("exit_structure")
            return f"{label}: {self._speaker.label(container.element_id)}"
        # At the top level, Up moves to the previous document line.
        if self.document.line_up():
            return self._cmd_read_line()
        return self._read_current()

    def _cmd_matrix(self) -> str:
        """Insert a 2x2 matrix and enter its first cell."""
        self.document.insert(Matrix("matrix", rows=2, cols=2, slots=[[], [], [], []]))
        return f"{self._speaker.label('matrix')}, {self._announce_cell()}"

    def _cmd_matrix_add_row(self) -> str:
        if not self.document.matrix_add_row():
            return self._read_current()
        return self._speaker.label("matrix_add_row")

    def _cmd_matrix_add_column(self) -> str:
        if not self.document.matrix_add_column():
            return self._read_current()
        return self._speaker.label("matrix_add_column")

    def _announce_cell(self) -> str:
        """Speak the current matrix cell position, then read its content."""
        cell = self.document.cursor_cell()
        if cell is None:
            return self._read_current()
        row, column = cell
        position = self._message("matrix_cell")
        position = position.replace("{row}", str(row + 1)).replace("{column}", str(column + 1))
        content = self._speaker.sequence(self.document.current_sequence())
        return f"{position}: {content}"

    def _cmd_new_line(self) -> str:
        if not self.document.new_line():
            return self._read_current()
        return self._speaker.label("new_line")

    def _cmd_next_slot(self) -> str:
        container = self.document.current_container()
        if container is None:
            return self._read_current()
        in_matrix = self.document.current_matrix() is not None
        slot_number = self.document.next_slot()
        if slot_number is None:
            label = self._speaker.label("exit_structure")
            return f"{label}: {self._speaker.label(container.element_id)}"
        if in_matrix:
            return self._announce_cell()
        return f"{self._speaker.label(SLOT_ID)} {slot_number + 1}"

    def _cmd_delete(self) -> str:
        node = self.document.delete()
        if node is not None:
            return f"{self._speaker.label('delete')}: {self._speaker.node(node)}"
        if self.document.merge_with_next_line():
            return self._cmd_read_line()
        return self._read_current()

    def _cmd_backspace(self) -> str:
        node = self.document.backspace()
        if node is not None:
            return f"{self._speaker.label('backspace')}: {self._speaker.node(node)}"
        if self.document.merge_with_previous_line():
            return self._cmd_read_line()
        return self._speaker.label("line_start")

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
    keymap: str | None = None,
    addons: Registry | bool = True,
) -> Editor:
    """Build an editor loading every table from the data directory.

    ``language`` resolves the language-dependent tables (falling back to
    the reference language, E6); ``profile`` limits elements by level (A7);
    ``reader`` optionally replaces the table speaker when reading a whole
    expression (see :mod:`disvimat.backends`); ``keymap`` loads a keyboard
    profile that overrides the default strokes, so the editor can answer to
    another editor's commands (Lambda, EDICO…); ``addons`` discovers
    extensions (True), skips them (False), or takes a ready registry.
    """
    directory = directory or data_dir()
    registry = addons if isinstance(addons, Registry) else (load_addons() if addons else Registry())
    # Add-on commands become catalogue elements, so key resolution and the
    # user-level checks treat them exactly like built-in commands.
    catalog = Catalog(
        load_table(directory / "elements.json", Element).entries + registry.elements()
    )
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
    if keymap:
        # The profile is loaded last, so its strokes win over the defaults;
        # anything it leaves out keeps the built-in binding.
        path = keymap_path(directory, keymap)
        if not path.is_file():
            raise ValueError(f"unknown keymap: {keymap!r}")
        key_tables.append(load_table(path, KeyEntry))
    if registry.key_entries():
        key_tables.append(
            Table[KeyEntry](table="keys_addons", version=1, entries=registry.key_entries())
        )
    glyphs: Table[GlyphEntry] = load_table(directory / "glyphs.json", GlyphEntry)
    labels_table: Table[LabelEntry] = load_table(
        language_table_path(directory, "labels", language), LabelEntry
    )
    labels = Table[LabelEntry](
        table=labels_table.table,
        version=labels_table.version,
        language=labels_table.language,
        entries=[*labels_table.entries, *registry.label_entries(language)],
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
        addons=registry,
    )
