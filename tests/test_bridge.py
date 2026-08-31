"""The bridge: the editor as one object both front ends drive.

The FastAPI endpoints and the browser under Pyodide perform the same
operations. Written twice they would drift, the way the two keyboard
mappings did, so they are written once and these tests hold that one copy
to its promises.
"""

import json
from typing import Any

import pytest

from disvimat.bridge import Bridge, BridgeError
from disvimat.core.dvm import from_dvm


def view(payload: str) -> dict[str, Any]:
    return dict(json.loads(payload))


def type_all(bridge: Bridge, text: str) -> str:
    payload = bridge.state()
    for character in text:
        payload = bridge.press(character, character)
    return payload


# --- what crosses the boundary ----------------------------------------------


def test_every_answer_is_json_with_the_four_things_a_page_needs() -> None:
    """One string crosses, so nothing has to be marshalled or freed."""
    bridge = Bridge(language="en")
    answer = view(bridge.press("Ctrl+F", None))
    assert set(answer) == {"text", "position", "speech", "mathml"}
    assert answer["text"] == "(□∕□)"
    assert isinstance(answer["position"], int)
    assert answer["speech"]
    assert answer["mathml"].startswith("<math")


def test_a_printable_key_is_tried_as_a_sign_before_being_typed() -> None:
    bridge = Bridge(language="en")
    assert view(bridge.press("+", "+"))["text"] == "+"
    assert view(bridge.press("7", "7"))["text"] == "+7"


def test_an_unassigned_stroke_leaves_the_document_alone() -> None:
    bridge = Bridge(language="en")
    type_all(bridge, "1")
    assert view(bridge.press("Ctrl+Shift+Q", None))["text"] == "1"


# --- documents ---------------------------------------------------------------


def test_opening_an_exam_applies_its_restrictions() -> None:
    teacher = Bridge(language="es", profile="exam")
    type_all(teacher, "12")
    exam = teacher.export("dvm")

    student = Bridge(language="es")
    student.open(exam)
    assert "3" not in view(student.press("Ctrl+Return", None))["speech"]


def test_a_saved_document_keeps_the_profile_it_was_opened_under() -> None:
    teacher = Bridge(language="es", profile="exam")
    type_all(teacher, "1")
    student = Bridge(language="es")
    student.open(teacher.export("dvm"))
    assert from_dvm(student.export("dvm")).profile == "exam"


def test_a_malformed_document_is_reported_not_raised_raw() -> None:
    bridge = Bridge(language="en")
    with pytest.raises(BridgeError):
        bridge.open("{not json at all")


def test_unsupported_xhtml_is_reported() -> None:
    bridge = Bridge(language="en")
    with pytest.raises(BridgeError):
        bridge.import_xhtml("<html><body><math><mfrac/></math></body></html>")


def test_braille_export_says_so_when_there_is_no_source() -> None:
    """Braille never falls back across languages: it is refused instead."""
    bridge = Bridge(language="fr")
    with pytest.raises(BridgeError, match="braille"):
        bridge.export("brl")


def test_an_unknown_export_format_is_refused() -> None:
    with pytest.raises(BridgeError, match="unknown export"):
        Bridge(language="en").export("pdf")


def test_the_document_can_be_exported_as_xhtml() -> None:
    bridge = Bridge(language="en")
    type_all(bridge, "1")
    exported = bridge.export("xhtml")
    assert exported.startswith("<?xml")
    assert "<math" in exported


# --- the MathML cache --------------------------------------------------------
#
# Only the edited line can have changed, so the rest is served from the
# cache and a key stroke costs the same in a long document as in a short.


def mathml(bridge: Bridge) -> str:
    return str(view(bridge.state())["mathml"])


def test_the_cache_returns_what_a_fresh_render_would() -> None:
    """The only thing that must never change: the MathML itself."""
    cached = Bridge(language="en")
    type_all(cached, "1+2")
    cached.press("Return", None)
    type_all(cached, "3*4")

    fresh = Bridge(language="en")
    type_all(fresh, "1+2")
    fresh.press("Return", None)
    type_all(fresh, "3*4")
    fresh._mathml_cache.clear()
    assert mathml(cached) == mathml(fresh)


def test_untouched_lines_are_not_rendered_again() -> None:
    bridge = Bridge(language="en")
    renders = 0
    original = bridge._exporter.mathml

    def counting(nodes: Any) -> Any:
        nonlocal renders
        renders += 1
        return original(nodes)

    bridge._exporter.mathml = counting  # type: ignore[method-assign]

    for _ in range(5):
        bridge.press("Return", None)

    renders = 0
    bridge.state()
    assert renders == 0, "asking for the state again re-rendered six lines"

    bridge.press("7", "7")  # only the last line changes
    assert renders == 1, "editing one line of six rendered more than one"


def test_editing_a_line_invalidates_only_that_line() -> None:
    bridge = Bridge(language="en")
    type_all(bridge, "1")
    bridge.press("Return", None)
    type_all(bridge, "2")
    bridge.state()

    bridge.press("Up", None)  # back to the first line
    assert "<mn>15</mn>" in view(bridge.press("5", "5"))["mathml"]


def test_undo_is_not_served_from_the_cache() -> None:
    bridge = Bridge(language="en")
    type_all(bridge, "12")
    assert "<mn>12</mn>" in mathml(bridge)
    assert "<mn>1</mn>" in view(bridge.press("Ctrl+Z", None))["mathml"]


def test_the_cache_does_not_grow_without_bound() -> None:
    """Revisions are never reused, so stale entries have to be dropped."""
    bridge = Bridge(language="en")
    for _ in range(200):
        bridge.press("1", "1")
    assert len(bridge._mathml_cache) == len(bridge._workspace.editor.document.lines)


def test_deleted_lines_leave_no_entry_behind() -> None:
    bridge = Bridge(language="en")
    for _ in range(10):
        bridge.press("Return", None)
    bridge.state()
    assert len(bridge._mathml_cache) == 11
    for _ in range(10):
        bridge.press("Backspace", None)  # merges each line into the one above
    bridge.state()
    assert len(bridge._mathml_cache) == 1
