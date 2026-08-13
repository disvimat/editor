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


@dataclass
class Matrix:
    """A two-dimensional grid of cells (rows x columns).

    ``slots`` holds the cells flat, in row-major order (length
    ``rows * cols``), which lets the cursor descend into a matrix cell with
    the very same ``(node index, slot index)`` machinery used for a
    structure's slots — a matrix is, for navigation, a container of slots.
    """

    element_id: str
    rows: int
    cols: int
    slots: list[list["Node"]]

    def cell(self, row: int, col: int) -> list["Node"]:
        return self.slots[row * self.cols + col]


Node = Character | Sign | Structure | Matrix

#: Anything the cursor can descend into: it exposes ``slots``.
Container = Structure | Matrix


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
        self._next_revision = 0
        self._revisions: list[int] = [self._new_revision()]
        # Per line: whether an undo snapshot still refers to that exact list
        # object, so changing it must go through a private copy first.
        self._shared: list[bool] = [False]

    # --- revisions ---------------------------------------------------------

    def revisions(self) -> list[int]:
        """One revision number per line, for caches keyed on line content.

        Turning a line into MathML, braille or speech is work that only
        needs redoing when the line changes, but a line is a plain list:
        nothing about it says whether it was touched. A revision is a
        number that changes whenever its line's content does, so a
        presentation layer can cache against it.

        Revisions are **never reused** — not even by undo, which restores
        content but takes fresh numbers — so a cached rendering can never
        be served for different content that happens to sit at the same
        line index.

        The editing methods below keep these current. Code that changes the
        tree behind the document's back (an add-on reaching into ``lines``)
        must call :meth:`invalidate`.
        """
        return list(self._revisions)

    def invalidate(self) -> None:
        """Mark every line as changed, for edits made outside this class."""
        self._revisions = [self._new_revision() for _ in self.lines]

    def _new_revision(self) -> int:
        self._next_revision += 1
        return self._next_revision

    def _touch(self, line: int) -> None:
        """Record that the given line's content changed."""
        self._revisions[line] = self._new_revision()

    # --- copy on write ------------------------------------------------------

    def _edit(self, *lines: int) -> None:
        """Prepare to change the given lines: snapshot, unshare, renumber.

        Undo keeps snapshots of the whole document, but a key stroke only
        ever changes one line, so a snapshot holds *references* to the line
        objects rather than copies of them (see :meth:`_snapshot`). The
        price is this rule: a line a snapshot still points at must never be
        changed in place. Unsharing buys the line a private copy the first
        time it is edited after a snapshot, and only then.

        **Call this before taking any reference into a line** — a slot
        list, a matrix, the line itself. Unsharing swaps the line object,
        so a reference taken earlier would point at the copy the snapshot
        now owns, and the change would land in the undo history instead of
        the document.
        """
        self._save_snapshot()
        for line in lines:
            self._unshare(line)
            self._touch(line)

    def _unshare(self, line: int) -> None:
        """Give the line a private copy if a snapshot still refers to it."""
        if self._shared[line]:
            self.lines[line] = copy.deepcopy(self.lines[line])
            self._shared[line] = False

    def _share_all(self) -> None:
        """Note that every line is now reachable from a snapshot."""
        self._shared = [True] * len(self.lines)

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
            assert isinstance(node, Container)
            sequence = node.slots[slot_index]
        return sequence

    def cursor_path(self) -> list[tuple[int, int]]:
        return list(self._cursor.path)

    def cursor_index(self) -> int:
        return self._cursor.index

    def current_container(self) -> Container | None:
        """The structure or matrix whose slot holds the cursor, if any."""
        if not self._cursor.path:
            return None
        sequence = self.current_line()
        for node_index, slot_index in self._cursor.path[:-1]:
            node = sequence[node_index]
            assert isinstance(node, Container)
            sequence = node.slots[slot_index]
        node = sequence[self._cursor.path[-1][0]]
        assert isinstance(node, Container)
        return node

    def current_structure(self) -> Structure | None:
        """The structure whose slot holds the cursor, if any."""
        container = self.current_container()
        return container if isinstance(container, Structure) else None

    def current_matrix(self) -> Matrix | None:
        """The matrix whose cell holds the cursor, if any."""
        container = self.current_container()
        return container if isinstance(container, Matrix) else None

    def cursor_cell(self) -> tuple[int, int] | None:
        """The (row, column) of the cursor inside a matrix, if in one."""
        matrix = self.current_matrix()
        if matrix is None:
            return None
        return divmod(self._cursor.path[-1][1], matrix.cols)

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
        """Insert a node at the cursor; containers are entered at slot 1."""
        self._edit(self._cursor.line)
        sequence = self.current_sequence()
        sequence.insert(self._cursor.index, node)
        if isinstance(node, Container):
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
        self.invalidate()
        # The caller may well keep its own references to these lines, so
        # treat them as shared: the first edit of each buys a private copy.
        self._share_all()
        last = len(self.lines) - 1
        self._cursor = _Cursor(line=last, index=len(self.lines[last]))

    def new_line(self) -> bool:
        """Split the current line at the cursor into a new line below.

        Only acts at the top level; inside a structure it does nothing.
        """
        if not self.at_top_level():
            return False
        self._edit(self._cursor.line)
        line = self.current_line()  # private since _edit; safe to cut
        tail = line[self._cursor.index :]
        del line[self._cursor.index :]
        self.lines.insert(self._cursor.line + 1, tail)
        # The tail is a brand new list of nodes that are private too, so no
        # snapshot can reach it: it starts out unshared.
        self._revisions.insert(self._cursor.line + 1, self._new_revision())
        self._shared.insert(self._cursor.line + 1, False)
        self._cursor = _Cursor(line=self._cursor.line + 1, index=0)
        return True

    def merge_with_previous_line(self) -> bool:
        """Join the current line onto the previous one (backspace at start)."""
        if not self.at_top_level() or self._cursor.index != 0 or self._cursor.line == 0:
            return False
        # Both lines have to become private: the nodes of the line that goes
        # end up inside the line that stays, so leaving the source shared
        # would hand the snapshot's nodes to the live document.
        self._edit(self._cursor.line - 1, self._cursor.line)
        previous = self.lines[self._cursor.line - 1]
        join = len(previous)
        previous.extend(self.current_line())
        del self.lines[self._cursor.line]
        del self._revisions[self._cursor.line]
        del self._shared[self._cursor.line]
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
        # As in merge_with_previous_line: the nodes of the next line move
        # into this one, so both must be private first.
        self._edit(self._cursor.line, self._cursor.line + 1)
        self.current_line().extend(self.lines[self._cursor.line + 1])
        del self.lines[self._cursor.line + 1]
        del self._revisions[self._cursor.line + 1]
        del self._shared[self._cursor.line + 1]
        return True

    def backspace(self) -> Node | None:
        """Delete the node to the left of the cursor and return it."""
        if self._cursor.index == 0:
            return None
        self._edit(self._cursor.line)
        sequence = self.current_sequence()
        self._cursor.index -= 1
        return sequence.pop(self._cursor.index)

    def delete(self) -> Node | None:
        """Delete the node to the right of the cursor and return it."""
        if self._cursor.index >= len(self.current_sequence()):
            return None
        self._edit(self._cursor.line)
        # Read the sequence again: _edit may have swapped in a private copy
        # of the line, and the old one now belongs to the undo snapshot.
        return self.current_sequence().pop(self._cursor.index)

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

    def enter(self) -> Container | None:
        """Enter the first slot of the container right of the cursor."""
        node = self.node_right()
        if not isinstance(node, Container):
            return None
        self._cursor.path.append((self._cursor.index, 0))
        self._cursor.index = 0
        return node

    def exit(self) -> Container | None:
        """Leave the current container; the cursor lands just after it."""
        container = self.current_container()
        if container is None:
            return None
        node_index, _ = self._cursor.path.pop()
        self._cursor.index = node_index + 1
        return container

    def next_slot(self) -> int | None:
        """Move to the next slot of the current container.

        Returns the index of the new slot; when the cursor was in the last
        slot (or outside any container) it leaves the container, like
        :meth:`exit`, and returns ``None``.
        """
        container = self.current_container()
        if container is None:
            return None
        node_index, slot_index = self._cursor.path[-1]
        if slot_index + 1 >= len(container.slots):
            self.exit()
            return None
        self._cursor.path[-1] = (node_index, slot_index + 1)
        self._cursor.index = 0
        return slot_index + 1

    # --- matrices ---------------------------------------------------------

    def move_in_matrix(self, delta_row: int, delta_col: int) -> tuple[int, int] | None:
        """Move the cursor between matrix cells; returns the new (row, col)."""
        matrix = self.current_matrix()
        if matrix is None:
            return None
        node_index, flat = self._cursor.path[-1]
        row, col = divmod(flat, matrix.cols)
        new_row, new_col = row + delta_row, col + delta_col
        if not (0 <= new_row < matrix.rows and 0 <= new_col < matrix.cols):
            return None
        self._cursor.path[-1] = (node_index, new_row * matrix.cols + new_col)
        self._cursor.index = 0
        return new_row, new_col

    def matrix_add_row(self) -> bool:
        """Add an empty row below the cursor's row (cursor stays in a matrix)."""
        if self.current_matrix() is None:
            return False
        self._edit(self._cursor.line)
        # Find the matrix again: _edit may have replaced the line, and the
        # matrix found before it would be the snapshot's copy.
        matrix = self.current_matrix()
        assert matrix is not None
        row = self._cursor.path[-1][1] // matrix.cols
        at = (row + 1) * matrix.cols
        matrix.slots[at:at] = [[] for _ in range(matrix.cols)]
        matrix.rows += 1
        return True

    def matrix_add_column(self) -> bool:
        """Add an empty column after the cursor's column."""
        if self.current_matrix() is None:
            return False
        self._edit(self._cursor.line)
        matrix = self.current_matrix()  # as above: re-read after unsharing
        assert matrix is not None
        col = self._cursor.path[-1][1] % matrix.cols
        # Insert one cell after ``col`` in every row, walking backwards so
        # earlier insertions do not shift later positions.
        for row in reversed(range(matrix.rows)):
            matrix.slots.insert(row * matrix.cols + col + 1, [])
        matrix.cols += 1
        return True

    # --- undo -------------------------------------------------------------

    def undo(self) -> bool:
        if not self._past:
            return False
        self._future.append(self._snapshot())
        self.lines, self._cursor = self._past.pop()
        self._restored()
        return True

    def redo(self) -> bool:
        if not self._future:
            return False
        self._past.append(self._snapshot())
        self.lines, self._cursor = self._future.pop()
        self._restored()
        return True

    def _restored(self) -> None:
        """Settle the bookkeeping after undo or redo put lines back."""
        # The restored lines may still be referenced by other snapshots —
        # an untouched line is shared by every snapshot taken while it went
        # unchanged — so none of them may be edited in place.
        self._share_all()
        # And they get fresh revisions rather than reviving old ones, so no
        # cache can match a rendering to content it was not built from.
        self.invalidate()

    def _snapshot(self) -> tuple[list[Line], _Cursor]:
        """The state to restore, sharing every line with the document.

        This is a *shallow* copy: a new list holding the same line objects.
        Deep-copying the whole document on every key stroke made the cost
        of typing grow with the length of the document, which for a long
        document is felt as lag. The lines are protected instead by the
        copy-on-write rule in :meth:`_edit`, so only lines that actually
        change are ever copied.
        """
        cursor = _Cursor(
            line=self._cursor.line,
            path=list(self._cursor.path),  # the steps are tuples: immutable
            index=self._cursor.index,
        )
        return list(self.lines), cursor

    def _save_snapshot(self) -> None:
        self._past.append(self._snapshot())
        del self._past[: -self.UNDO_LIMIT]
        self._future.clear()
        # Every line is now reachable from a snapshot, so the next change to
        # any of them must go through a private copy.
        self._share_all()
