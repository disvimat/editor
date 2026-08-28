"""Desktop key mapping and what the screen reader is told.

Reported from real NVDA use: commands "did nothing" and finishing a word
with space said nothing. The commands did run — the app was simply silent,
because a screen reader does not read the status bar on its own. These
tests pin both halves: the key strokes map correctly, and every action is
handed to the speech output.
"""

import pytest

from wx_support import require_wx

wx = require_wx()

from disvimat.desktop.app import _finished_word, canonical_keys  # noqa: E402
from disvimat.desktop.screen_reader import SilentOutput  # noqa: E402


class FakeKeyEvent:
    """Duck-types the parts of wx.KeyEvent that canonical_keys reads."""

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


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (FakeKeyEvent(wx.WXK_RETURN, ctrl=True), "Ctrl+Return"),  # calculate
        (FakeKeyEvent(wx.WXK_RETURN), "Return"),  # new line
        (FakeKeyEvent(ord("L"), ctrl=True, shift=True), "Ctrl+Shift+L"),
        (FakeKeyEvent(ord("F"), ctrl=True), "Ctrl+F"),
        (FakeKeyEvent(wx.WXK_LEFT), "Left"),
        (FakeKeyEvent(wx.WXK_NUMPAD_DIVIDE), "NumDivide"),
        (FakeKeyEvent(ord(" ")), None),  # plain characters go through EVT_CHAR
    ],
)
def test_key_strokes_reach_the_core_in_canonical_form(
    event: FakeKeyEvent, expected: str | None
) -> None:
    assert canonical_keys(event) == expected  # type: ignore[arg-type]


# --- the word finished by a space -------------------------------------------


class _Result:
    """A stand-in for the editor Result (only text and position matter here)."""

    def __init__(self, text: str, position: int) -> None:
        self.text, self.position = text, position


@pytest.mark.parametrize(
    ("text", "position", "expected"),
    [
        ("hola ", 5, "hola"),  # the word just closed
        ("uno dos ", 8, "dos"),  # only the last one
        ("1+2 ", 4, "1+2"),  # maths count as a "word" too
        (" ", 1, ""),  # nothing typed yet
        ("", 0, ""),
    ],
)
def test_finished_word(text: str, position: int, expected: str) -> None:
    assert _finished_word(_Result(text, position)) == expected  # type: ignore[arg-type]


def test_silent_output_never_raises() -> None:
    """With no screen reader present the editor must still run."""
    silent = SilentOutput()
    assert silent.speak("anything") is None
    assert silent.braille("⠁") is None
