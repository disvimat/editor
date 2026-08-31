"""Getting wxPython in the tests, and refusing to pretend when it matters.

The desktop is the interface blind users reach through NVDA, so its tests
are the ones that must not quietly vanish. ``pytest.importorskip`` on its
own turns a broken install into a green build: the run reports success
while testing nothing.

So the skip is conditional. Where the desktop is meant to be exercised —
the Windows job in CI, and any developer who sets it — the environment
variable makes a missing wxPython a failure instead of a skip.
"""

import os
from types import ModuleType

import pytest

#: Set this where wxPython must be present; a missing one then fails.
REQUIRE_ENV = "DISVIMAT_REQUIRE_DESKTOP"


def require_wx() -> ModuleType:
    """The ``wx`` module: skipping, or failing where it has to be there."""
    if os.environ.get(REQUIRE_ENV):
        import wx  # a hard failure here is the point

        return wx
    return pytest.importorskip("wx", reason="the desktop interface needs wxPython")
