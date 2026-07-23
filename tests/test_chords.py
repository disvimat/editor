"""Chorded key strokes ("Ctrl+G, P"), the convention EDICO uses.

A chord is a comma-separated sequence of strokes. Resolution is a tiny
state machine: the first stroke leaves the keyboard *pending*, the next one
completes it. These tests cover the machine in isolation and end to end
through the editor, since the desktop and web adapters both rely on
``chord_pending()`` to route the second, bare stroke as a key rather than
typing it.
"""

import json
import shutil
from pathlib import Path

import pytest

from disvimat.core.editor import create_editor
from disvimat.core.keyboard import Keyboard, State, parse_chord
from disvimat.core.tables import Catalog, KeyEntry, Table

DATA = Path(__file__).resolve().parents[1] / "data"


def keyboard_with(*bindings: tuple[str, str], level: int | None = None) -> Keyboard:
    catalog = Catalog.load(DATA / "elements.json")
    table = Table[KeyEntry](
        table="keys_test",
        version=1,
        entries=[KeyEntry(id=element_id, keys=keys) for element_id, keys in bindings],
    )
    return Keyboard(catalog, table, level=level)


# --- the state machine -------------------------------------------------------


def test_parse_chord_splits_on_the_separator() -> None:
    assert parse_chord("Ctrl+G, P") == ("Ctrl+G", "P")
    assert parse_chord("Ctrl+F") == ("Ctrl+F",)


def test_a_single_stroke_resolves_at_once() -> None:
    keyboard = keyboard_with(("plus", "Ctrl+P"))
    result = keyboard.feed("Ctrl+P")
    assert result.state is State.RESOLVED
    assert result.element is not None
    assert result.element.id == "plus"


def test_a_chord_waits_then_resolves() -> None:
    keyboard = keyboard_with(("plus", "Ctrl+G, P"))
    first = keyboard.feed("Ctrl+G")
    assert first.state is State.PENDING
    assert keyboard.pending
    second = keyboard.feed("P")
    assert second.state is State.RESOLVED
    assert second.element is not None
    assert second.element.id == "plus"
    assert not keyboard.pending


def test_an_unknown_second_stroke_abandons_the_chord() -> None:
    keyboard = keyboard_with(("plus", "Ctrl+G, P"))
    keyboard.feed("Ctrl+G")
    result = keyboard.feed("Z")  # does not continue the chord, nothing else
    assert result.state is State.UNKNOWN
    assert not keyboard.pending


def test_a_second_stroke_can_start_a_fresh_binding() -> None:
    keyboard = keyboard_with(("plus", "Ctrl+G, P"), ("minus", "Ctrl+M"))
    keyboard.feed("Ctrl+G")
    result = keyboard.feed("Ctrl+M")  # abandons the chord, resolves on its own
    assert result.state is State.RESOLVED
    assert result.element is not None
    assert result.element.id == "minus"


def test_reset_abandons_a_pending_chord() -> None:
    keyboard = keyboard_with(("plus", "Ctrl+G, P"))
    keyboard.feed("Ctrl+G")
    keyboard.reset()
    assert not keyboard.pending


# --- end to end through the editor ------------------------------------------


@pytest.fixture
def data_copy(tmp_path: Path) -> Path:
    target = tmp_path / "data"
    shutil.copytree(DATA, target)
    return target


def _user_keymap(tmp_path: Path, entries: list[dict[str, str]]) -> Path:
    path = tmp_path / "user_keys.json"
    path.write_text(
        json.dumps({"table": "keys_user", "version": 1, "language": None, "entries": entries}),
        encoding="utf-8",
    )
    return path


def test_editor_consumes_the_first_stroke_silently(tmp_path: Path) -> None:
    keymap = _user_keymap(tmp_path, [{"id": "plus", "keys": "Ctrl+G, P"}])
    editor = create_editor(DATA, language="en", user_keymap=keymap)
    pending = editor.press("Ctrl+G")
    assert pending is not None
    assert pending.speech == ""  # consumed; nothing announced yet
    assert editor.chord_pending()


def test_editor_completes_the_chord(tmp_path: Path) -> None:
    keymap = _user_keymap(tmp_path, [{"id": "plus", "keys": "Ctrl+G, P"}])
    editor = create_editor(DATA, language="en", user_keymap=keymap)
    editor.press("Ctrl+G")
    result = editor.press("P")
    assert result is not None
    assert result.speech.startswith("plus")
    assert not editor.chord_pending()
