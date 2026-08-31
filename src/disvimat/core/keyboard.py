"""Key stroke resolution from the A2/A3/A4 tables, with chord support.

Key strokes reach the core already normalised to the canonical format
("+", "Left", "Ctrl+F", "Ctrl+Shift+R"), so desktop and web share the
same bindings.

A binding may be a **chord**: a comma-separated sequence of strokes, like
``"Ctrl+G, P"`` (the convention used by EDICO for Greek letters, titles,
etc.). Resolution is therefore a tiny state machine — a stroke that only
begins a chord leaves the keyboard *pending* until the next stroke
completes it, or something else resets it.
"""

from dataclasses import dataclass
from enum import Enum, auto

from disvimat.core.elements import Element, ElementType
from disvimat.core.tables import Catalog, KeyEntry, Table

#: How the strokes of a chord are joined in a binding's ``keys`` value.
CHORD_SEPARATOR = ", "

Sequence = tuple[str, ...]


def parse_chord(keys: str) -> Sequence:
    """Split a binding's ``keys`` into its sequence of strokes."""
    return tuple(part for part in keys.split(CHORD_SEPARATOR) if part)


class State(Enum):
    RESOLVED = auto()  # a full binding fired
    PENDING = auto()  # a chord has begun; waiting for the next stroke
    UNKNOWN = auto()  # nothing matched


@dataclass(frozen=True)
class KeyResult:
    """The outcome of feeding one stroke to the keyboard."""

    state: State
    element: Element | None = None


class Keyboard:
    """Resolves key strokes (single or chorded) into catalogue elements.

    With ``level`` set (profiles, A7), signs and structures above that
    level resolve to nothing; commands are always available.
    """

    def __init__(
        self, catalog: Catalog, *tables: Table[KeyEntry], level: int | None = None
    ) -> None:
        self._level = level
        self._by_sequence: dict[Sequence, Element] = {}
        self._prefixes: set[Sequence] = set()
        self._pending: Sequence = ()
        for table in tables:
            for entry in table.entries:
                # The A3 conditions grammar is still pending; only
                # unconditional entries load. A conditional one would be
                # dropped here without a word, so integrity.unsupported_
                # conditions fails the build before a table can rely on it.
                # A later binding for the same sequence wins, which is how
                # keymaps override defaults.
                if entry.condition is None:
                    self._add(parse_chord(entry.keys), catalog[entry.id])

    def _add(self, sequence: Sequence, element: Element) -> None:
        self._by_sequence[sequence] = element
        for length in range(1, len(sequence)):
            self._prefixes.add(sequence[:length])

    def reset(self) -> None:
        """Abandon any chord in progress."""
        self._pending = ()

    @property
    def pending(self) -> bool:
        """Whether a chord has begun and is waiting for its next stroke."""
        return bool(self._pending)

    def feed(self, stroke: str) -> KeyResult:
        """Advance the state machine with one canonical stroke."""
        candidate = (*self._pending, stroke)
        resolved = self._match(candidate)
        if resolved is not None:
            self._pending = ()
            return KeyResult(State.RESOLVED, resolved)
        if candidate in self._prefixes:
            self._pending = candidate
            return KeyResult(State.PENDING)
        # The chord in progress does not continue with this stroke: abandon
        # it and try the stroke on its own (a fresh binding or chord start).
        self._pending = ()
        fresh = (stroke,)
        resolved = self._match(fresh)
        if resolved is not None:
            return KeyResult(State.RESOLVED, resolved)
        if fresh in self._prefixes:
            self._pending = fresh
            return KeyResult(State.PENDING)
        return KeyResult(State.UNKNOWN)

    def _match(self, sequence: Sequence) -> Element | None:
        element = self._by_sequence.get(sequence)
        if (
            element is not None
            and element.type is not ElementType.COMMAND
            and self._level is not None
            and element.level > self._level
        ):
            return None
        return element
