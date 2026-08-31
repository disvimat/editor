"""The canonical stroke names, and both interfaces agreeing on them.

The ``keys`` of every key table are canonical names ("Left", "NumDivide"),
but the desktop and the web get different things from their platform: wx
sends key codes, the browser sends ``KeyboardEvent`` fields. That mapping
used to be written out twice, once per adapter, and the two had already
drifted: the keypad's division key inserted a fraction on the desktop and a
division *sign* on the web — the same physical key, two different
documents, from a project whose architecture claims both interfaces behave
alike by construction.

Now both read ``data/keys_platform.json``. These tests hold them to it.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from disvimat.core.editor import create_editor
from disvimat.core.keyboard import parse_chord
from disvimat.core.tables import (
    KeyEntry,
    PlatformKeyEntry,
    Table,
    data_dir,
    load_table,
)
from disvimat.web.app import create_app, platform_keys_json

DATA = Path(__file__).resolve().parents[1] / "data"
KEY_TABLES = ("keys_signs.json", "keys_commands.json", "keys_numpad.json")

#: Modifier names are not keys in their own right; they prefix a stroke.
MODIFIERS = frozenset({"Ctrl", "Alt", "Shift"})


def platform_table() -> Table[PlatformKeyEntry]:
    return load_table(DATA / "keys_platform.json", PlatformKeyEntry)


def canonical_names() -> set[str]:
    return {entry.canonical for entry in platform_table().entries}


def special_names_used() -> set[str]:
    """Every non-printable stroke name the key tables actually ask for."""
    used: set[str] = set()
    for filename in KEY_TABLES:
        table: Table[KeyEntry] = load_table(DATA / filename, KeyEntry)
        for entry in table.entries:
            for stroke in parse_chord(entry.keys):
                name = stroke.split("+")[-1]
                # A single character comes from the keyboard layout, not
                # from this table; anything longer is a named key.
                if len(name) > 1 and name not in MODIFIERS:
                    used.add(name)
    return used


# --- the contract -----------------------------------------------------------


def test_every_named_key_the_tables_ask_for_can_be_produced() -> None:
    missing = special_names_used() - canonical_names()
    assert not missing, f"no interface can produce these bindings: {sorted(missing)}"


def test_the_keypad_bindings_are_covered() -> None:
    """A4: they were dead on the web, which is how the drift showed up."""
    assert {"NumAdd", "NumSubtract", "NumMultiply", "NumDivide"} <= canonical_names()


def test_the_browser_is_offered_every_canonical_name() -> None:
    served = {entry["canonical"] for entry in json.loads(platform_keys_json())}
    assert served == canonical_names()


def test_the_browser_can_tell_the_keypad_apart_from_the_main_row() -> None:
    """``key`` is "/" for both; only ``code`` distinguishes them."""
    by_canonical = {e["canonical"]: e for e in json.loads(platform_keys_json())}
    for name in ("NumAdd", "NumSubtract", "NumMultiply", "NumDivide"):
        assert by_canonical[name]["code"], f"{name} needs a KeyboardEvent.code"
    assert by_canonical["NumDivide"]["code"] == "NumpadDivide"
    assert by_canonical["Left"]["key"] == "ArrowLeft"


def test_no_two_entries_claim_the_same_platform_key() -> None:
    keys: list[str] = []
    codes: list[str] = []
    for entry in platform_table().entries:
        if entry.dom_key:
            keys.append(entry.dom_key)
        if entry.dom_code:
            codes.append(entry.dom_code)
    assert len(keys) == len(set(keys)), "a KeyboardEvent.key maps to two names"
    assert len(codes) == len(set(codes)), "a KeyboardEvent.code maps to two names"


def test_the_page_carries_the_mapping_so_the_first_key_stroke_works() -> None:
    """It is embedded, not fetched: the user may type before any round trip."""
    page = TestClient(create_app()).get("/").text
    assert '<script type="application/json" id="platform-keys">' in page
    assert "NumpadDivide" in page
    assert "{{platform_keys}}" not in page
    # Nothing in the payload may close the script block.
    payload = page.split('id="platform-keys">')[1].split("</script>")[0]
    assert json.loads(payload)


# --- the behaviour the drift produced ---------------------------------------


def test_the_keypad_division_key_makes_a_fraction_not_a_division_sign() -> None:
    """The bug, pinned: on the web this used to insert '÷' instead."""
    editor = create_editor(language="es")
    result = editor.press("NumDivide")
    assert result is not None
    assert result.text == "(□∕□)"


def test_the_main_row_slash_still_makes_a_division_sign() -> None:
    editor = create_editor(language="es")
    result = editor.press("/") or editor.type_character("/")
    assert result.text == "÷"


# --- the guard rails --------------------------------------------------------
#
# What makes a half-added binding fail the build rather than go quiet on one
# interface. Without these, the validators are untested scaffolding.


def test_a_binding_the_browser_could_never_send_is_refused() -> None:
    with pytest.raises(ValidationError, match="browser"):
        PlatformKeyEntry(id="ghost", canonical="Ghost", wx=("WXK_F13",))


def test_a_binding_the_desktop_could_never_send_is_refused() -> None:
    with pytest.raises(ValidationError, match="desktop"):
        PlatformKeyEntry(id="ghost", canonical="Ghost", dom_key="F13")


def test_a_canonical_name_must_look_like_one() -> None:
    """The tables spell them in upper camel case; "left" would never match."""
    with pytest.raises(ValidationError):
        PlatformKeyEntry(id="left", canonical="left", dom_key="ArrowLeft", wx=("WXK_LEFT",))


# --- the desktop half -------------------------------------------------------


def test_the_desktop_produces_exactly_the_same_names() -> None:
    pytest.importorskip("wx", reason="the desktop interface needs wxPython")
    from disvimat.desktop.app import _SPECIAL_KEYS

    assert set(_SPECIAL_KEYS.values()) == canonical_names()


def test_every_wx_name_in_the_table_exists() -> None:
    wx = pytest.importorskip("wx", reason="the desktop interface needs wxPython")
    for entry in platform_table().entries:
        for name in entry.wx:
            assert hasattr(wx, name), f"{entry.canonical}: wx has no {name}"


def test_the_table_travels_with_the_installed_package() -> None:
    """data_dir() is what a wheel or a frozen .exe actually reads."""
    assert (data_dir() / "keys_platform.json").is_file()
