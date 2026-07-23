"""Personal key reassignments, checked for conflicts before saving.

The user's own keymap loads at the highest priority (over the defaults, a
compatibility profile and add-ons), so someone migrating from another
editor can bend the shortcuts to what their fingers know. The rebind tool
guards that power: it refuses bindings that cannot work (unknown command,
chord overlap) and warns about the ones that quietly steal a stroke.
"""

import json
from pathlib import Path

from disvimat.core.editor import create_editor
from disvimat.core.integrity import chord_shadow_conflicts, key_conflicts
from disvimat.core.tables import Catalog, KeyEntry, Table
from disvimat.tools import rebind

DATA = Path(__file__).resolve().parents[1] / "data"


def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


def table(*bindings: tuple[str, str]) -> Table[KeyEntry]:
    return Table[KeyEntry](
        table="keys_test",
        version=1,
        entries=[KeyEntry(id=element_id, keys=keys) for element_id, keys in bindings],
    )


# --- conflict detection ------------------------------------------------------


def test_binding_an_unknown_command_is_refused() -> None:
    check = rebind.check_assignment(catalog(), DATA, [], "nope", "Ctrl+B")
    assert not check.ok
    assert check.error is not None
    assert "unknown command" in check.error


def test_a_free_stroke_binds_without_a_warning() -> None:
    check = rebind.check_assignment(catalog(), DATA, [], "fraction", "Ctrl+Shift+B")
    assert check.ok
    assert check.displaced is None


def test_stealing_a_stroke_warns_which_command_loses_it() -> None:
    # Ctrl+Return is the built-in "calculate" stroke.
    check = rebind.check_assignment(catalog(), DATA, [], "fraction", "Ctrl+Return")
    assert check.ok  # allowed — that is the whole point of a reassignment
    assert check.displaced == "calculate"


def test_a_chord_that_shadows_an_existing_binding_is_refused() -> None:
    user = [KeyEntry(id="plus", keys="Ctrl+G, P")]
    check = rebind.check_assignment(catalog(), DATA, user, "minus", "Ctrl+G")
    assert not check.ok
    assert check.error is not None
    assert "chord conflict" in check.error


# --- editing the user entries ------------------------------------------------


def test_assign_adds_a_binding() -> None:
    entries = rebind.assign([], "fraction", "Ctrl+B")
    assert entries == [KeyEntry(id="fraction", keys="Ctrl+B")]


def test_assign_moves_a_stroke_off_another_command() -> None:
    # No two user entries may share a stroke, or they would truly conflict.
    entries = rebind.assign([KeyEntry(id="minus", keys="Ctrl+B")], "fraction", "Ctrl+B")
    assert entries == [KeyEntry(id="fraction", keys="Ctrl+B")]


def test_assign_replaces_the_same_command() -> None:
    entries = rebind.assign([KeyEntry(id="fraction", keys="Ctrl+B")], "fraction", "Ctrl+D")
    assert entries == [KeyEntry(id="fraction", keys="Ctrl+D")]


def test_clear_removes_a_binding() -> None:
    entries = rebind.clear([KeyEntry(id="fraction", keys="Ctrl+B")], "fraction")
    assert entries == []


def test_read_and_write_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "user_keys.json"
    rebind.write_user_keymap(path, [KeyEntry(id="fraction", keys="Ctrl+B")])
    assert rebind.read_user_keymap(path) == [KeyEntry(id="fraction", keys="Ctrl+B")]


def test_reading_a_missing_file_is_empty(tmp_path: Path) -> None:
    assert rebind.read_user_keymap(tmp_path / "absent.json") == []


# --- integrity helpers -------------------------------------------------------


def test_key_conflicts_flags_a_shared_stroke() -> None:
    conflicts = key_conflicts(table(("plus", "Ctrl+B"), ("minus", "Ctrl+B")))
    assert conflicts == {"Ctrl+B": ["plus", "minus"]}


def test_chord_shadow_conflicts_flags_a_prefix_overlap() -> None:
    conflicts = chord_shadow_conflicts(table(("plus", "Ctrl+G"), ("minus", "Ctrl+G, P")))
    assert conflicts == {"Ctrl+G": "Ctrl+G, P"}


def test_chord_shadow_conflicts_ignores_unrelated_chords() -> None:
    conflicts = chord_shadow_conflicts(table(("plus", "Ctrl+G, P"), ("minus", "Ctrl+H, M")))
    assert conflicts == {}


# --- the user keymap wins end to end ----------------------------------------


def test_the_user_binding_beats_a_compatibility_profile(tmp_path: Path) -> None:
    keymap_dir = DATA / "keymaps"  # ship dir has empty lambda/edico scaffolds
    assert keymap_dir.is_dir()
    path = tmp_path / "user_keys.json"
    path.write_text(
        json.dumps(
            {
                "table": "keys_user",
                "version": 1,
                "language": None,
                "entries": [{"id": "fraction", "keys": "Ctrl+B"}],
            }
        ),
        encoding="utf-8",
    )
    editor = create_editor(DATA, language="en", keymap="lambda", user_keymap=path)
    result = editor.press("Ctrl+B")
    assert result is not None
    assert result.speech.startswith("fraction")
