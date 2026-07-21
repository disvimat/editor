"""Key stroke resolution from the A2/A3/A4 tables.

Key strokes reach the core already normalised to the canonical table
format ("+", "Left", "Ctrl+F", "Ctrl+Shift+R"), so desktop and web share
exactly the same bindings.
"""

from disvimat.core.elements import Element, ElementType
from disvimat.core.tables import Catalog, KeyEntry, Table


class Keyboard:
    """Translates a canonical key stroke into the assigned catalogue element.

    With ``level`` set (profiles, A7), signs and structures above that
    level resolve to nothing; commands are always available.
    """

    def __init__(
        self, catalog: Catalog, *tables: Table[KeyEntry], level: int | None = None
    ) -> None:
        self._level = level
        self._by_keys: dict[str, Element] = {}
        for table in tables:
            for entry in table.entries:
                # The grammar of the A3 conditions is still pending; for now
                # only unconditional entries are loaded.
                if entry.condition is None:
                    self._by_keys[entry.keys] = catalog[entry.id]

    def resolve(self, keys: str) -> Element | None:
        element = self._by_keys.get(keys)
        if (
            element is not None
            and element.type is not ElementType.COMMAND
            and self._level is not None
            and element.level > self._level
        ):
            return None
        return element
