"""Reassign a key stroke safely — without silent conflicts.

Users coming from another editor (EDICO, Lambda) want their own shortcuts.
This edits a personal keymap that the editor loads at the highest priority,
so a user binding wins over the defaults, a compatibility profile and
add-ons. Before writing, it checks for conflicts:

- **Refused:** binding a command that does not exist, or a chord that would
  make another unreachable (``Ctrl+G`` versus ``Ctrl+G, P`` — after the
  first stroke the editor can only do one thing).
- **Warned:** taking a stroke that another command currently uses. The
  reassignment is allowed (that is the point), but you are told which
  command loses the stroke, so nothing is silent.

Usage::

    python -m disvimat.tools.rebind show "Ctrl+F"
    python -m disvimat.tools.rebind set fraction "Ctrl+B"
    python -m disvimat.tools.rebind clear fraction
    python -m disvimat.tools.rebind list

The personal keymap lives at ``$DISVIMAT_USER_KEYMAP`` or
``~/.disvimat/user_keys.json``.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.keyboard import parse_chord
from disvimat.core.tables import (
    Catalog,
    KeyEntry,
    data_dir,
    load_table,
    user_keymap_path,
)

#: The key tables that ship with the editor, lowest priority first.
_DEFAULT_TABLES = ("keys_signs.json", "keys_commands.json", "keys_numpad.json")


@dataclass(frozen=True)
class Check:
    """The verdict on a proposed reassignment."""

    ok: bool
    displaced: str | None = None  # a command that would lose the stroke
    error: str | None = None  # a hard conflict that forbids the change


def _default_owners(directory: Path) -> dict[str, str]:
    """Map ``keys`` -> command id for the shipped bindings (last wins)."""
    owners: dict[str, str] = {}
    for name in _DEFAULT_TABLES:
        for entry in load_table(directory / name, KeyEntry).entries:
            owners[entry.keys] = entry.id
    return owners


def read_user_keymap(path: Path) -> list[KeyEntry]:
    if not path.is_file():
        return []
    return list(load_table(path, KeyEntry).entries)


def write_user_keymap(path: Path, entries: list[KeyEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "table": "keys_user",
        "version": 1,
        "language": None,
        "entries": [{"id": entry.id, "keys": entry.keys} for entry in entries],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_assignment(
    catalog: Catalog, directory: Path, user: list[KeyEntry], element_id: str, keys: str
) -> Check:
    """Decide whether ``element_id`` may be bound to ``keys``."""
    if element_id not in catalog:
        return Check(False, error=f"unknown command: {element_id!r}")

    # All bindings currently in force, except this command's own.
    bindings: dict[str, str] = _default_owners(directory)
    for entry in user:
        bindings[entry.keys] = entry.id
    others = {k: i for k, i in bindings.items() if i != element_id}

    new = parse_chord(keys)
    for other_keys in others:
        existing = parse_chord(other_keys)
        shorter, longer = sorted((new, existing), key=len)
        if longer[: len(shorter)] == shorter and shorter != longer:
            return Check(
                False,
                error=f"chord conflict: {keys!r} overlaps {other_keys!r}",
            )

    return Check(True, displaced=others.get(keys))


def assign(user: list[KeyEntry], element_id: str, keys: str) -> list[KeyEntry]:
    """Return the user entries with ``element_id`` bound to ``keys``."""
    kept = [e for e in user if e.id != element_id and e.keys != keys]
    return [*kept, KeyEntry(id=element_id, keys=keys)]


def clear(user: list[KeyEntry], element_id: str) -> list[KeyEntry]:
    return [entry for entry in user if entry.id != element_id]


# --- command line -----------------------------------------------------------


def _command_for(directory: Path, user: list[KeyEntry], keys: str) -> str | None:
    owners = _default_owners(directory)
    for entry in user:
        owners[entry.keys] = entry.id
    return owners.get(keys)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        print(__doc__, file=sys.stderr)
        return 2

    directory = data_dir()
    catalog = Catalog.load(directory / "elements.json")
    path = user_keymap_path()
    user = read_user_keymap(path)
    action = arguments[0]

    if action == "list":
        if not user:
            print("no personal key reassignments")
        for entry in user:
            print(f"{entry.keys}\t{entry.id}")
        return 0

    if action == "show" and len(arguments) == 2:
        owner = _command_for(directory, user, arguments[1])
        print(owner if owner else f"{arguments[1]!r} is not bound to anything")
        return 0

    if action == "set" and len(arguments) == 3:
        element_id, keys = arguments[1], arguments[2]
        check = check_assignment(catalog, directory, user, element_id, keys)
        if not check.error:
            write_user_keymap(path, assign(user, element_id, keys))
            print(f"bound {element_id} to {keys}")
            if check.displaced:
                print(f"  note: {keys} was used by {check.displaced}, which loses it")
            return 0
        print(check.error, file=sys.stderr)
        return 1

    if action == "clear" and len(arguments) == 2:
        write_user_keymap(path, clear(user, arguments[1]))
        print(f"cleared any personal binding for {arguments[1]}")
        return 0

    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
