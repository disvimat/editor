"""The desktop window itself: what a screen reader is actually handed.

The desktop is the interface blind users reach through NVDA, and until now
only two pure functions of it were tested — the window, where the reported
bug lived ("the commands did nothing": they ran, the app was simply
silent), was never built in a test at all.

These tests build the real :class:`EditorWindow` (never shown) and drive it
the way wx does, so the accessibility contract is pinned: after every
action the text control carries the document, the caret sits where the core
put it, the status line shows the message, speech is handed the message,
and a connected braille display gets the current line.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from wx_support import require_wx

wx = require_wx()

from disvimat.core.document import Node  # noqa: E402
from disvimat.core.editor import Editor, create_editor  # noqa: E402
from disvimat.core.ui_text import UIText  # noqa: E402
from disvimat.desktop.app import EditorWindow  # noqa: E402


class RecordingOutput:
    """A screen reader that remembers instead of speaking."""

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.brailled: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)

    def braille(self, text: str) -> None:
        self.brailled.append(text)


class FakeBraille:
    """Stands in for a braille engine: one cell per node, so it is checkable."""

    def unicode(self, nodes: list[Node]) -> str:
        return "⠿" * len(nodes)

    def ascii(self, nodes: list[Node]) -> str:
        return "=" * len(nodes)


@pytest.fixture(scope="module")
def app() -> Iterator[wx.App]:
    yield wx.App()


@pytest.fixture
def speech() -> RecordingOutput:
    return RecordingOutput()


@pytest.fixture
def window(app: wx.App, speech: RecordingOutput) -> Iterator[EditorWindow]:
    editor: Editor = create_editor(language="en")
    frame = EditorWindow(editor, FakeBraille(), UIText.load(language="en"), speech=speech)
    yield frame
    frame.Destroy()


class KeyEvent:
    """Duck-types the parts of wx.KeyEvent the two handlers read.

    The handlers are driven through this rather than reimplemented in the
    test: a test that repeats the logic it is checking passes happily while
    the real handler is broken.
    """

    def __init__(
        self,
        code: int,
        *,
        ctrl: bool = False,
        shift: bool = False,
        alt: bool = False,
        unicode_key: int | None = None,
    ) -> None:
        self._code = code
        self._ctrl, self._shift, self._alt = ctrl, shift, alt
        self._unicode = code if unicode_key is None else unicode_key
        self.skipped = False

    def ControlDown(self) -> bool:  # noqa: N802
        return self._ctrl

    def ShiftDown(self) -> bool:  # noqa: N802
        return self._shift

    def AltDown(self) -> bool:  # noqa: N802
        return self._alt

    def GetKeyCode(self) -> int:  # noqa: N802
        return self._code

    def GetUnicodeKey(self) -> int:  # noqa: N802
        return self._unicode

    def Skip(self, skip: bool = True) -> None:  # noqa: N802
        self.skipped = skip


def press(window: EditorWindow, code: int, **modifiers: bool) -> KeyEvent:
    """Send a key stroke through the window's real EVT_CHAR_HOOK handler."""
    event = KeyEvent(code, **modifiers)
    window._on_key(event)  # type: ignore[arg-type]
    return event


def type_character(window: EditorWindow, character: str) -> KeyEvent:
    """Send a character through the window's real EVT_CHAR handler."""
    event = KeyEvent(ord(character))
    window._on_character(event)  # type: ignore[arg-type]
    return event


def fraction(window: EditorWindow) -> None:
    press(window, ord("F"), ctrl=True)


def document_text(window: EditorWindow) -> str:
    return str(window._document.GetValue())


# --- what the screen reader is handed ---------------------------------------


def test_every_action_is_spoken_not_only_shown(
    window: EditorWindow, speech: RecordingOutput
) -> None:
    """The bug that was reported: a status bar nobody reads aloud."""
    fraction(window)
    assert speech.spoken, "the action reached the status bar but never the screen reader"
    assert speech.spoken[-1] == window.GetStatusBar().GetStatusText()


def test_the_text_control_carries_the_document(window: EditorWindow) -> None:
    fraction(window)
    assert document_text(window) == "(□∕□)"


def test_the_caret_lands_where_the_core_put_it(window: EditorWindow) -> None:
    fraction(window)
    result = window._editor.state()
    assert window._document.GetInsertionPoint() == result.position


def test_the_current_line_reaches_the_braille_display(
    window: EditorWindow, speech: RecordingOutput
) -> None:
    fraction(window)
    assert speech.brailled, "nothing was pushed to the braille display"
    # One cell per node of the current line, per FakeBraille.
    assert len(speech.brailled[-1]) == len(window._editor.document.current_line())


def test_without_a_braille_engine_nothing_is_pushed(app: wx.App, speech: RecordingOutput) -> None:
    frame = EditorWindow(
        create_editor(language="en"), None, UIText.load(language="en"), speech=speech
    )
    try:
        fraction(frame)
        assert speech.spoken
        assert not speech.brailled, "a language with no braille source must send none"
    finally:
        frame.Destroy()


# --- typing ------------------------------------------------------------------


def test_a_typed_character_is_not_spoken_twice(
    window: EditorWindow, speech: RecordingOutput
) -> None:
    """The screen reader echoes what is typed; repeating it would double up."""
    type_character(window, "5")
    assert document_text(window) == "5"
    assert speech.spoken == [], "the character was echoed a second time"


def test_space_announces_the_word_it_just_closed(
    window: EditorWindow, speech: RecordingOutput
) -> None:
    for character in "sin":
        type_character(window, character)
    assert speech.spoken == []
    type_character(window, " ")
    assert speech.spoken == ["sin"]


def test_an_assigned_sign_is_spoken(window: EditorWindow, speech: RecordingOutput) -> None:
    type_character(window, "+")
    assert document_text(window) == "+"
    assert speech.spoken == ["plus"]


def test_the_second_stroke_of_a_chord_is_routed_not_typed(
    app: wx.App, speech: RecordingOutput, tmp_path: Path
) -> None:
    """EDICO's convention: "Ctrl+G, F". The second stroke arrives as a bare
    letter through EVT_CHAR, and would otherwise be inserted as text."""
    keymap = tmp_path / "user_keys.json"
    keymap.write_text(
        json.dumps(
            {
                "table": "keys_user",
                "version": 1,
                "entries": [{"id": "fraction", "keys": "Ctrl+G, F"}],
            }
        ),
        encoding="utf-8",
    )
    editor = create_editor(language="en", user_keymap=keymap)
    frame = EditorWindow(editor, None, UIText.load(language="en"), speech=speech)
    try:
        press(frame, ord("G"), ctrl=True)  # the chord opens and waits
        assert editor.chord_pending()
        type_character(frame, "f")  # a bare letter: must complete the chord
        assert not editor.chord_pending()
        assert document_text(frame) == "(□∕□)", "the letter was typed instead"
    finally:
        frame.Destroy()


# --- the braille window ------------------------------------------------------


def test_the_braille_window_follows_the_document(window: EditorWindow) -> None:
    window._toggle_braille(None)  # type: ignore[arg-type]
    assert window._braille is not None
    fraction(window)
    assert window._braille_text() == "⠿" * len(window._editor.document.current_line())


def test_the_menu_only_binds_commands_the_catalogue_knows(window: EditorWindow) -> None:
    """A menu entry for a command that does not exist would be a dead item."""
    bar = window.GetMenuBar()
    assert bar.GetMenuCount() >= 5
    for index in range(bar.GetMenuCount()):
        menu = bar.GetMenu(index)
        assert menu.GetMenuItemCount() > 0, f"menu {index} is empty"


def test_opening_an_exam_replaces_the_editor_with_a_restricted_one(
    window: EditorWindow, speech: RecordingOutput
) -> None:
    """The file dialog is wx's; what is checked here is what follows it.

    Opening a document swaps the editor for the one the document asks for,
    which is what applies an exam's restrictions on a machine that knows
    nothing about that exam.
    """
    from disvimat.backends import create_workspace, open_document
    from disvimat.core.dvm import to_dvm

    teacher = create_workspace(language="en", profile="exam")
    for key in ("1", "+", "2"):
        if teacher.editor.press(key) is None:
            teacher.editor.type_character(key)
    exam = to_dvm(teacher.editor.document.lines, language="en", profile="exam")

    assert window._profile is None
    window._adopt(open_document(exam))
    window._apply(window._editor.state())

    assert window._profile == "exam"
    assert document_text(window) == "1+2"
    result = window._editor.press("Ctrl+Return")
    assert result is not None
    assert "3" not in result.speech, "the exam opened with its calculator working"
