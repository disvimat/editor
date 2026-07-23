"""Speaking through the user's screen reader (NVDA, JAWS…).

The editor produces a spoken string for every action ("fraction, blank 1",
"result: 5"). Putting it in the status bar is not enough: a screen reader
does not read the status bar on its own, so from the user's side the
command looks like it did nothing. This module says it out loud.

It uses `accessible_output2`, which talks to NVDA and JAWS through their
official controller libraries and falls back to SAPI. When no output is
available every call is a no-op, so the editor still runs (and the status
bar keeps showing the same text).
"""

import contextlib
from typing import Protocol


class SpeechOutput(Protocol):
    """What the window needs from a screen reader."""

    def speak(self, text: str) -> None: ...
    def braille(self, text: str) -> None: ...


class SilentOutput:
    """Used when no screen reader or speech engine is available."""

    name = "none"

    def speak(self, text: str) -> None:
        return None

    def braille(self, text: str) -> None:
        return None


class AccessibleOutput:
    """Speech and braille through ``accessible_output2``."""

    def __init__(self, output: object) -> None:
        self._output = output
        self.name = type(output).__name__

    def speak(self, text: str) -> None:
        if not text:
            return
        # interrupt: each action replaces the previous announcement, which is
        # what makes fast typing usable. Speech must never break editing.
        with contextlib.suppress(Exception):
            self._output.speak(text, interrupt=True)  # type: ignore[attr-defined]

    def braille(self, text: str) -> None:
        writer = getattr(self._output, "braille", None)
        if writer is None or not text:
            return
        with contextlib.suppress(Exception):
            writer(text)


def create_output() -> SpeechOutput:
    """The best available screen-reader output, or a silent one."""
    try:
        from accessible_output2.outputs.auto import Auto  # noqa: PLC0415
    except ImportError:
        return SilentOutput()
    try:
        auto = Auto()
        if auto.get_first_available_output() is None:
            return SilentOutput()
        return AccessibleOutput(auto)
    except Exception:  # noqa: BLE001 - a broken speech stack must not stop us
        return SilentOutput()
