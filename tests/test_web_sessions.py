"""Web adapter: the MathML cache and the lifetime of a session.

Two things the editor needs from the web adapter but that no other test
covers: rendering a key stroke must not get slower as the document grows,
and a session must not live in memory for ever.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from disvimat.web.app import _Session, _SessionStore, create_app


class _Clock:
    """A hand-wound clock, so the tests never wait for real time."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def session(language: str = "en") -> _Session:
    return _Session(language=language, profile=None)


# --- the MathML cache ------------------------------------------------------


def type_line(instance: _Session, text: str) -> None:
    for character in text:
        instance.editor.type_character(character)


def test_the_cache_returns_what_a_fresh_render_would() -> None:
    """The only thing that must never change: the MathML itself."""
    instance = session()
    type_line(instance, "1+2")
    instance.editor.press("Return")
    type_line(instance, "3*4")
    cached = instance.mathml()

    fresh = session()
    type_line(fresh, "1+2")
    fresh.editor.press("Return")
    type_line(fresh, "3*4")
    fresh._mathml_cache.clear()
    assert cached == fresh.mathml()


def test_untouched_lines_are_not_rendered_again() -> None:
    instance = session()
    renders = 0
    original = instance.exporter.mathml

    def counting(nodes: Any) -> Any:
        nonlocal renders
        renders += 1
        return original(nodes)

    instance.exporter.mathml = counting  # type: ignore[method-assign]

    for _ in range(5):
        instance.editor.press("Return")
    instance.mathml()  # first pass: every line rendered once
    assert renders == 6

    renders = 0
    instance.editor.type_character("7")  # only the last line changes
    instance.mathml()
    assert renders == 1


def test_editing_a_line_invalidates_only_that_line() -> None:
    instance = session()
    type_line(instance, "1")
    instance.editor.press("Return")
    type_line(instance, "2")
    instance.mathml()

    instance.editor.press("Up")  # to the first line
    instance.editor.type_character("5")
    assert "<mn>15</mn>" in instance.mathml()


def test_undo_is_not_served_from_the_cache() -> None:
    instance = session()
    type_line(instance, "12")
    assert "<mn>12</mn>" in instance.mathml()
    instance.editor.press("Ctrl+Z")
    assert "<mn>1</mn>" in instance.mathml()


def test_the_cache_does_not_grow_without_bound() -> None:
    """Revisions are never reused, so stale entries have to be dropped."""
    instance = session()
    for _ in range(200):
        instance.editor.type_character("1")
        instance.mathml()
    assert len(instance._mathml_cache) == len(instance.editor.document.lines)


def test_deleted_lines_leave_no_entry_behind() -> None:
    instance = session()
    for _ in range(10):
        instance.editor.press("Return")
    instance.mathml()
    assert len(instance._mathml_cache) == 11
    for _ in range(10):
        instance.editor.press("Backspace")  # merges each line into the one above
    instance.mathml()
    assert len(instance._mathml_cache) == 1


# --- the session store -----------------------------------------------------


def test_an_idle_session_expires() -> None:
    clock = _Clock()
    store = _SessionStore(ttl=100.0, clock=clock)
    store.add("a", session())
    clock.advance(99.0)
    assert store.get("a") is not None
    clock.advance(101.0)
    assert store.get("a") is None
    assert len(store) == 0


def test_using_a_session_keeps_it_alive() -> None:
    clock = _Clock()
    store = _SessionStore(ttl=100.0, clock=clock)
    store.add("a", session())
    for _ in range(5):
        clock.advance(60.0)
        assert store.get("a") is not None, "a session in use must not time out"


def test_one_session_expiring_does_not_take_the_others() -> None:
    clock = _Clock()
    store = _SessionStore(ttl=100.0, clock=clock)
    store.add("old", session())
    clock.advance(60.0)
    store.add("new", session())
    clock.advance(60.0)
    assert store.get("old") is None
    assert store.get("new") is not None


def test_the_store_is_capped_and_drops_the_least_recently_used() -> None:
    clock = _Clock()
    store = _SessionStore(ttl=10_000.0, max_sessions=3, clock=clock)
    for name in ("a", "b", "c"):
        store.add(name, session())
        clock.advance(1.0)
    store.get("a")  # 'a' is now the most recently used, so 'b' is the oldest
    clock.advance(1.0)
    store.add("d", session())
    assert len(store) == 3
    assert store.get("b") is None
    assert store.get("a") is not None
    assert store.get("c") is not None
    assert store.get("d") is not None


def test_an_unknown_session_is_simply_absent() -> None:
    assert _SessionStore().get("nope") is None


# --- what the page sees ----------------------------------------------------


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


def test_an_expired_session_answers_404_so_the_page_can_recover(clock: _Clock) -> None:
    store = _SessionStore(ttl=100.0, clock=clock)
    client = TestClient(create_app(store))
    session_id = client.post("/api/session").json()["session"]
    assert client.post(f"/api/session/{session_id}/key", json={"keys": "1"}).status_code == 200

    clock.advance(200.0)
    response = client.post(f"/api/session/{session_id}/key", json={"keys": "1"})
    assert response.status_code == 404
    assert "expired" in response.json()["detail"]

    # And a new session is available at once, so the page can carry on.
    assert client.post("/api/session").status_code == 200


def test_the_page_carries_the_expiry_message_for_the_live_region() -> None:
    """The status bar is not a live region: the message has to be announced,
    so it must reach the page in the user's language, from the ui table."""
    client = TestClient(create_app())
    page = client.get("/?language=es").text
    assert "data-session-expired=" in page
    assert "caduc" in page
    assert "{{session_expired}}" not in page
