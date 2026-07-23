"""Keyboard profiles: answering to another editor's commands.

A keymap is loaded after the built-in key tables, so the strokes it defines
win and everything it leaves out keeps the default. That is what lets a
user coming from Lambda or EDICO keep the commands they know without any
code change.
"""

import json
from pathlib import Path

import pytest

from disvimat.core.editor import create_editor
from disvimat.core.integrity import unknown_ids
from disvimat.core.tables import (
    Catalog,
    KeyEntry,
    available_keymaps,
    keymap_path,
    load_table,
)

DATA = Path(__file__).resolve().parents[1] / "data"


def write_keymap(directory: Path, name: str, entries: list[dict[str, str]]) -> None:
    folder = directory / "keymaps"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(
        json.dumps({"table": f"keys_{name}", "version": 1, "language": None, "entries": entries}),
        encoding="utf-8",
    )


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    """A writable copy of data/ so tests can add keymaps."""
    import shutil

    target = tmp_path / "data"
    shutil.copytree(DATA, target)
    return target


# --- the bundled profiles ---------------------------------------------------


def test_bundled_keymaps_are_listed() -> None:
    names = available_keymaps(DATA)
    assert "lambda" in names
    assert "edico" in names


@pytest.mark.parametrize("name", ["lambda", "edico"])
def test_bundled_keymaps_reference_known_ids(name: str) -> None:
    """A typo in a profile must fail the build, not silently do nothing."""
    catalog = Catalog.load(DATA / "elements.json")
    table = load_table(keymap_path(DATA, name), KeyEntry)
    assert unknown_ids(table, catalog) == set()


def test_an_empty_profile_keeps_the_defaults() -> None:
    """The shipped scaffolds are empty, so behaviour is unchanged."""
    editor = create_editor(DATA, language="en", keymap="lambda")
    result = editor.press("Ctrl+F")  # the built-in fraction stroke
    assert result is not None
    assert result.speech.startswith("fraction")


# --- overriding ---------------------------------------------------------------


def test_a_profile_stroke_wins_over_the_default(data_copy: Path) -> None:
    write_keymap(data_copy, "demo", [{"id": "fraction", "keys": "Ctrl+B"}])
    editor = create_editor(data_copy, language="en", keymap="demo")
    result = editor.press("Ctrl+B")  # the profile's stroke
    assert result is not None
    assert result.speech.startswith("fraction")


def test_what_a_profile_omits_keeps_working(data_copy: Path) -> None:
    write_keymap(data_copy, "demo", [{"id": "fraction", "keys": "Ctrl+B"}])
    editor = create_editor(data_copy, language="en", keymap="demo")
    assert editor.press("Ctrl+Return") is not None  # calculate, untouched
    assert editor.press("Tab") is not None  # next slot, untouched


def test_a_profile_can_rebind_a_command(data_copy: Path) -> None:
    write_keymap(data_copy, "demo", [{"id": "calculate", "keys": "F9"}])
    editor = create_editor(data_copy, language="en", keymap="demo")
    editor.type_character("2")
    result = editor.press("F9")
    assert result is not None
    assert result.speech.startswith("result")


def test_unknown_keymap_is_reported_clearly() -> None:
    with pytest.raises(ValueError, match="unknown keymap"):
        create_editor(DATA, language="en", keymap="does-not-exist")


def test_no_keymap_is_the_default_behaviour() -> None:
    editor = create_editor(DATA, language="en")
    result = editor.press("Ctrl+F")
    assert result is not None
