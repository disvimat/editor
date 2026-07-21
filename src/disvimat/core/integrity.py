"""Cross-table integrity checks.

The tests use them (CI fails when a table is inconsistent: principle 5 of
the plan) and the table editor (prior decision "c") will use them to warn
about conflicts before saving.
"""

from disvimat.core.elements import ElementType, Record
from disvimat.core.tables import Catalog, KeyEntry, Table


def unknown_ids[R: Record](table: Table[R], catalog: Catalog) -> set[str]:
    """Ids referenced by the table that do not exist in the catalogue."""
    return {entry.id for entry in table.entries} - catalog.ids()


def uncovered_ids[R: Record](
    table: Table[R], catalog: Catalog, types: set[ElementType]
) -> set[str]:
    """Catalogue elements of the given types with no entry in the table."""
    covered = {entry.id for entry in table.entries}
    return {element.id for element in catalog if element.type in types} - covered


def key_conflicts(*tables: Table[KeyEntry]) -> dict[str, list[str]]:
    """Key strokes assigned to more than one element under the same condition.

    Accepts several tables so conflicts *between* them are detected too
    (e.g. a stroke used by both an A2 sign and an A3 command). Returns
    ``{key stroke: [conflicting ids]}``.
    """
    by_stroke: dict[tuple[str, str | None], list[str]] = {}
    for table in tables:
        for entry in table.entries:
            key = (entry.keys, entry.condition)
            by_stroke.setdefault(key, []).append(entry.id)
    return {
        keys if condition is None else f"{keys} [{condition}]": ids
        for (keys, condition), ids in by_stroke.items()
        if len(ids) > 1
    }
