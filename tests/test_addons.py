"""Add-ons (module A5): extending the editor without touching the core.

An add-on command must behave exactly like a built-in one — reachable by
its key stroke, spoken in the user's language, undoable — and a broken
add-on must never take the editor down.
"""

from pathlib import Path

import pytest

from disvimat.core.addons import MSG_ADDON_FAILED, Registry, load_addons
from disvimat.core.editor import Editor, create_editor

DATA = Path(__file__).resolve().parents[1] / "data"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "addons"


def shout(editor: Editor) -> str:
    return "shouted"


@pytest.fixture
def registry() -> Registry:
    registry = Registry()
    registry.add_command(
        id="shout",
        run=shout,
        keys="Ctrl+Alt+S",
        labels={"en": "shout", "es": "gritar"},
    )
    return registry


# --- a contributed command behaves like a built-in one ----------------------


def test_an_addon_command_runs_from_its_key(registry: Registry) -> None:
    editor = create_editor(DATA, language="en", addons=registry)
    result = editor.press("Ctrl+Alt+S")
    assert result is not None
    assert result.speech == "shouted"


def test_an_addon_command_is_in_the_catalogue(registry: Registry) -> None:
    editor = create_editor(DATA, language="en", addons=registry)
    assert "shout" in editor.catalog
    assert editor.catalog["shout"].category == "addon"


def test_an_addon_can_change_the_document(registry: Registry) -> None:
    def add_digit(editor: Editor) -> str:
        editor.type_character("7")
        return "added seven"

    registry.add_command(id="add_seven", run=add_digit, keys="Ctrl+Alt+7")
    editor = create_editor(DATA, language="en", addons=registry)
    result = editor.press("Ctrl+Alt+7")
    assert result is not None
    assert result.text == "7"
    assert result.speech == "added seven"
    # and it is undoable like anything else
    undone = editor.press("Ctrl+Z")
    assert undone is not None
    assert undone.text == ""


def test_labels_follow_the_users_language(registry: Registry) -> None:
    spanish = create_editor(DATA, language="es", addons=registry)
    assert spanish._speaker.label("shout") == "gritar"
    french = create_editor(DATA, language="fr", addons=registry)
    assert french._speaker.label("shout") == "shout"  # falls back to English


def test_a_command_without_a_key_is_still_registered(registry: Registry) -> None:
    registry.add_command(id="quiet", run=shout)
    editor = create_editor(DATA, language="en", addons=registry)
    assert "quiet" in editor.catalog
    assert editor.press("Ctrl+Alt+S") is not None  # the bound one still works


# --- failures are contained ---------------------------------------------------


def test_a_failing_command_does_not_break_the_editor() -> None:
    def explode(editor: Editor) -> str:
        raise RuntimeError("boom")

    registry = Registry()
    registry.add_command(id="explode", run=explode, keys="Ctrl+Alt+X")
    editor = create_editor(DATA, language="en", addons=registry)
    result = editor.press("Ctrl+Alt+X")
    assert result is not None
    assert result.speech == "the add-on could not run"  # from the messages table
    # the editor is still usable
    assert editor.press("Ctrl+F") is not None


def test_a_broken_addon_file_is_reported_not_raised(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("raise RuntimeError('bad')", encoding="utf-8")
    (tmp_path / "fine.py").write_text(
        "def register(registry):\n    registry.add_command(id='ok', run=lambda editor: 'ok')\n",
        encoding="utf-8",
    )
    registry = load_addons(tmp_path, entry_points=False)
    assert "ok" in registry.commands  # the good one still loaded
    assert any("broken.py" in error for error in registry.errors)


def test_a_module_without_register_is_reported(tmp_path: Path) -> None:
    (tmp_path / "nothing.py").write_text("value = 1\n", encoding="utf-8")
    registry = load_addons(tmp_path, entry_points=False)
    assert any("no register()" in error for error in registry.errors)


def test_duplicate_command_ids_are_refused(registry: Registry) -> None:
    with pytest.raises(ValueError, match="duplicate add-on command"):
        registry.add_command(id="shout", run=shout)


# --- discovery -----------------------------------------------------------------


def test_addons_can_be_disabled() -> None:
    editor = create_editor(DATA, language="en", addons=False)
    assert editor.addons.commands == {}


def test_the_bundled_example_addon_loads_and_works() -> None:
    registry = load_addons(EXAMPLES, entry_points=False)
    assert registry.errors == []
    assert "count_line" in registry.commands

    editor = create_editor(DATA, language="es", addons=registry)
    editor.type_character("1")
    editor.press("+")
    result = editor.press("Ctrl+Alt+C")
    assert result is not None
    assert result.speech == "1 characters, 1 signs, 0 structures"


def test_an_exporter_can_be_contributed() -> None:
    registry = Registry()
    registry.add_exporter(
        id="plain",
        extension=".txt",
        dump=lambda lines: f"{len(lines)} lines",
        labels={"es": "texto plano"},
    )
    exporter = registry.exporters["plain"]
    assert exporter.extension == ".txt"
    assert exporter.label("es") == "texto plano"
    assert exporter.dump([[], []]) == "2 lines"


def test_message_id_is_the_documented_one() -> None:
    assert MSG_ADDON_FAILED == "addon_failed"
