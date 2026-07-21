"""User profiles A7: levels limit the elements available."""

from pathlib import Path

import pytest

from disvimat.core.editor import create_editor

DATA = Path(__file__).resolve().parents[1] / "data"


def test_beginner_profile_blocks_higher_levels() -> None:
    editor = create_editor(DATA, profile="beginner")
    assert editor.press("Ctrl+Shift+R") is None  # nth root: level 3
    assert editor.press("Ctrl+R") is None  # square root: level 2
    assert editor.press("Ctrl+F") is not None  # fraction: level 1


def test_commands_do_not_depend_on_the_level() -> None:
    editor = create_editor(DATA, profile="beginner")
    editor.type_character("1")
    result = editor.press("Left")
    assert result is not None
    assert result.speech == "1"


def test_advanced_profile_allows_everything() -> None:
    editor = create_editor(DATA, profile="advanced")
    assert editor.press("Ctrl+Shift+R") is not None


def test_unknown_profile_gives_a_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown profile"):
        create_editor(DATA, profile="nonexistent")
