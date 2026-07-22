"""The document tree: nodes, cursor, editing and undo.

A document is a sequence of nodes; a structure holds slots, which are
themselves sequences of nodes. The cursor is a path descending through
structures plus an index inside the current sequence: the cursor always
sits *between* two nodes (or at one end).

This module neither speaks nor presents anything: it returns the nodes
affected by each operation and the presentation layers decide what to
show or announce (principle 1 of the plan).
"""

import copy
from dataclasses import dataclass, field


@dataclass
class Character:
    """A plain text character (digits, letters, spaces)."""

    text: str


@dataclass
class Sign:
    """A catalogue sign (no slots)."""

    element_id: str


@dataclass
class Structure:
    """A catalogue structure with its slots (one per unit of arity)."""

    element_id: str
    slots: list[list["Node"]]


Node = Character | Sign | Structure


@dataclass
class _Cursor:
    """Editing position: line + descent through structures + index.

    ``line`` selects the document line; ``path`` descends through
    structures within that line; each step is ``(structure node index,
    slot index)``; ``index`` is the position in the current sequence.
    """

    line: int = 0
    path: list[tuple[int, int]] = field(default_factory=list)
    index: int = 0


#: A line is a sequence of nodes (the same tree as before, one per line).
Line = list[Node]


class Document:
    """A multi-line document, with cursor and snapshot-based undo/redo."""

    #: Maximum number of snapshots kept for undo.
    UNDO_LIMIT = 200

    def __init__(self) -> None:
        self.lines: list[Line] = [[]]
        self._cursor = _Cursor()
        self._past: list[tuple[list[Line], _Cursor]] = []
        self._future: list[tuple[list[Line], _Cursor]] = []

    # --- state ------------------------------------------------------------

    @property
    def root(self) -> Line:
        """The current line's nodes (the sequence the cursor's line holds)."""
        return self.lines[self._cursor.line]

    def current_line(self) -> Line:
        return self.lines[self._cursor.line]

    def cursor_line(self) -> int:
        return self._cursor.line

    def line_count(self) -> int:
        return len(self.lines)

    def current_sequence(self) -> list[Node]:
        """The sequence (line or slot) the cursor is in."""
        sequence = self.current_line()
        for node_index, slot_index in self._cursor.path:
            node = sequence[node_index]
            assert isinstance(node, Structure)
            sequence = node.slots[slot_index]
        return sequence

    def cursor_path(self) -> list[tuple[int, int]]:
        return list(self._cursor.path)

    def cursor_index(self) -> int:
        return self._cursor.index

    def current_structure(self) -> Structure | None:
        """The structure whose slot holds the cursor, if any."""
        if not self._cursor.path:
            return None
        sequence = self.current_line()
        for node_index, slot_index in self._cursor.path[:-1]:
            node = sequence[node_index]
            assert isinstance(node, Structure)
            sequence = node.slots[slot_index]
        node = sequence[self._cursor.path[-1][0]]
        assert isinstance(node, Structure)
        return node

    def node_right(self) -> Node | None:
        """The node immediately to the right of the cursor, if any."""
        sequence = self.current_sequence()
        if self._cursor.index < len(sequence):
            return sequence[self._cursor.index]
        return None

    def at_top_level(self) -> bool:
        """Whether the cursor is directly on a line, not inside a structure."""
        return not self._cursor.path

    def is_empty(self) -> bool:
        return len(self.lines) == 1 and not self.lines[0]

    # --- editing ----------------------------------------------------------

    def insert(self, node: Node) -> None:
        """Insert a node at the cursor; structures are entered at slot 1."""
        self._save_snapshot()
        sequence = self.current_sequence()
        sequence.insert(self._cursor.index, node)
        if isinstance(node, Structure):
            self._cursor.path.append((self._cursor.index, 0))
            self._cursor.index = 0
        else:
            self._cursor.index += 1

    def load(self, nodes: list[Node]) -> None:
        """Replace the whole content with a single line (imports); undoable."""
        self.load_lines([nodes])

    def load_lines(self, lines: list[Line]) -> None:
        """Replace the whole document with the given lines; undoable."""
        self._save_snapshot()
        self.lines = lines if lines else [[]]
        last = len(self.lines) - 1
        self._cursor = _Cursor(line=last, index=len(self.lines[last]))

    def new_line(self) -> bool:
        """Split the current line at the cursor into a new line below.

        Only acts at the top level; inside a structure it does nothing.
        """
        if not self.at_top_level():
            return False
        self._save_snapshot()
        line = self.current_line()
        tail = line[self._cursor.index :]
        del line[self._cursor.index :]
        self.lines.insert(self._cursor.line + 1, tail)
        self._cursor = _Cursor(line=self._cursor.line + 1, index=0)
        return True

    def merge_with_previous_line(self) -> bool:
        """Join the current line onto the previous one (backspace at start)."""
        if not self.at_top_level() or self._cursor.index != 0 or self._cursor.line == 0:
            return False
        self._save_snapshot()
        previous = self.lines[self._cursor.line - 1]
        join = len(previous)
        previous.extend(self.current_line())
        del self.lines[self._cursor.line]
        self._cursor = _Cursor(line=self._cursor.line - 1, index=join)
        return True

    def merge_with_next_line(self) -> bool:
        """Join the next line onto the current one (delete at end)."""
        if (
            not self.at_top_level()
            or self._cursor.index != len(self.current_line())
            or self._cursor.line >= len(self.lines) - 1
        ):
            return False
        self._save_snapshot()
        self.current_line().extend(self.lines[self._cursor.line + 1])
        del self.lines[self._cursor.line + 1]
        return True

    def backspace(self) -> Node | None:
        """Delete the node to the left of the cursor and return it."""
        if self._cursor.index == 0:
            return None
        self._save_snapshot()
        sequence = self.current_sequence()
        self._cursor.index -= 1
        return sequence.pop(self._cursor.index)

    def delete(self) -> Node | None:
        """Delete the node to the right of the cursor and return it."""
        sequence = self.current_sequence()
        if self._cursor.index >= len(sequence):
            return None
        self._save_snapshot()
        return sequence.pop(self._cursor.index)

    # --- navigation -------------------------------------------------------

    def left(self) -> Node | None:
        """Move the cursor one node left; return the node crossed."""
        if self._cursor.index == 0:
            return None
        self._cursor.index -= 1
        return self.current_sequence()[self._cursor.index]

    def right(self) -> Node | None:
        """Move the cursor one node right; return the node crossed."""
        sequence = self.current_sequence()
        if self._cursor.index >= len(sequence):
            return None
        self._cursor.index += 1
        return sequence[self._cursor.index - 1]

    def to_line_start(self) -> None:
        self._cursor.index = 0

    def to_line_end(self) -> None:
        self._cursor.index = len(self.current_sequence())

    def line_up(self) -> bool:
        """Move to the previous document line (top level only)."""
        if not self.at_top_level() or self._cursor.line == 0:
            return False
        self._cursor.line -= 1
        self._cursor.index = len(self.current_line())
        return True

    def line_down(self) -> bool:
        """Move to the next document line (top level only)."""
        if not self.at_top_level() or self._cursor.line >= len(self.lines) - 1:
            return False
        self._cursor.line += 1
        self._cursor.index = len(self.current_line())
        return True

    def enter(self) -> Structure | None:
        """Enter the first slot of the structure right of the cursor."""
        node = self.node_right()
        if not isinstance(node, Structure):
            return None
        self._cursor.path.append((self._cursor.index, 0))
        self._cursor.index = 0
        return node

    def exit(self) -> Structure | None:
        """Leave the current structure; the cursor lands just after it."""
        structure = self.current_structure()
        if structure is None:
            return None
        node_index, _ = self._cursor.path.pop()
        self._cursor.index = node_index + 1
        return structure

    def next_slot(self) -> int | None:
        """Move to the next slot of the current structure.

        Returns the index of the new slot; when the cursor was in the last
        slot (or outside any structure) it leaves the structure, like
        :meth:`exit`, and returns ``None``.
        """
        structure = self.current_structure()
        if structure is None:
            return None
        node_index, slot_index = self._cursor.path[-1]
        if slot_index + 1 >= len(structure.slots):
            self.exit()
            return None
        self._cursor.path[-1] = (node_index, slot_index + 1)
        self._cursor.index = 0
        return slot_index + 1

    # --- undo -------------------------------------------------------------

    def undo(self) -> bool:
        if not self._past:
            return False
        self._future.append(self._snapshot())
        self.lines, self._cursor = self._past.pop()
        return True

    def redo(self) -> bool:
        if not self._future:
            return False
        self._past.append(self._snapshot())
        self.lines, self._cursor = self._future.pop()
        return True

    def _snapshot(self) -> tuple[list[Line], _Cursor]:
        return copy.deepcopy((self.lines, self._cursor))

    def _save_snapshot(self) -> None:
        self._past.append(self._snapshot())
        del self._past[: -self.UNDO_LIMIT]
        self._future.clear()
