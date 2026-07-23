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


def chord_shadow_conflicts(*tables: Table[KeyEntry]) -> dict[str, str]:
    """Chords where one binding makes another unreachable.

    ``"Ctrl+G"`` and ``"Ctrl+G, P"`` cannot both work: after ``Ctrl+G`` the
    editor either fires the first or waits for the second, never both. This
    reports ``{shorter chord: longer chord}`` for every such overlap, so a
    reassignment tool can refuse it. It complements :func:`key_conflicts`,
    which catches identical bindings.
    """
    from disvimat.core.keyboard import parse_chord

    sequences: dict[tuple[str, ...], str] = {}
    for table in tables:
        for entry in table.entries:
            if entry.condition is None:
                sequences[parse_chord(entry.keys)] = entry.keys
    conflicts: dict[str, str] = {}
    for sequence, keys in sequences.items():
        for length in range(1, len(sequence)):
            prefix = sequence[:length]
            if prefix in sequences:
                conflicts[sequences[prefix]] = keys
    return conflicts
