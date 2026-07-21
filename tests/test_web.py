"""Web API: the same core operations served over HTTP (web adapter)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from disvimat.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def new_session(client: TestClient, language: str = "en") -> str:
    response = client.post(f"/api/session?language={language}")
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == ""
    return str(data["session"])


def send(
    client: TestClient, session: str, keys: str, character: str | None = None
) -> dict[str, Any]:
    response = client.post(
        f"/api/session/{session}/key", json={"keys": keys, "character": character}
    )
    assert response.status_code == 200
    return dict(response.json())


def type_all(client: TestClient, session: str, strokes: list[str]) -> dict[str, Any]:
    view: dict[str, Any] = {}
    for stroke in strokes:
        view = send(client, session, stroke, stroke if len(stroke) == 1 else None)
    return view


def test_main_page_is_accessible_html(client: TestClient) -> None:
    body = client.get("/").text
    assert '<html lang="en">' in body
    assert 'role="application"' in body
    assert "aria-live" in body
    assert "{{" not in body  # every placeholder was substituted


def test_page_is_served_in_the_requested_language(client: TestClient) -> None:
    body = client.get("/?language=fr").text
    assert '<html lang="fr">' in body
    assert "Calculer" in body


def test_editing_a_fraction_produces_text_and_mathml(client: TestClient) -> None:
    session = new_session(client)
    view = type_all(client, session, ["1", "+", "Ctrl+F", "2", "Tab", "3"])
    assert view["text"] == "1+(2∕3)"
    assert "<mfrac" in view["mathml"]
    assert view["speech"] == "3"


def test_printable_character_is_tried_as_a_sign_first(client: TestClient) -> None:
    session = new_session(client)
    view = send(client, session, "+", "+")  # "+" is a sign, not literal text
    assert view["text"] == "+"
    assert view["speech"] == "plus"


def test_calculating_through_the_api(client: TestClient) -> None:
    session = new_session(client)
    type_all(client, session, ["2", "+", "3"])
    view = send(client, session, "Ctrl+Return")
    assert view["speech"] == "result: 5"


def test_import_and_export(client: TestClient) -> None:
    session = new_session(client)
    type_all(client, session, ["1", "+", "2"])
    xhtml = client.get(f"/api/session/{session}/export.xhtml")
    assert xhtml.status_code == 200
    assert "attachment" in xhtml.headers["content-disposition"]
    assert "<math" in xhtml.text

    other = new_session(client)
    view = client.post(f"/api/session/{other}/import", json={"xhtml": xhtml.text}).json()
    assert view["text"] == "1+2"


def test_bra_export_needs_braille_tables(client: TestClient) -> None:
    spanish = new_session(client, language="es")
    send(client, spanish, "1", "1")
    bra = client.get(f"/api/session/{spanish}/export.bra")
    assert bra.status_code == 200
    assert bra.text.strip() == "#a"

    # English has no braille tables: refused instead of serving Spanish braille
    english = new_session(client, language="en")
    send(client, english, "1", "1")
    assert client.get(f"/api/session/{english}/export.bra").status_code == 409


def test_unknown_session_gives_404(client: TestClient) -> None:
    response = client.post("/api/session/nonexistent/key", json={"keys": "1", "character": "1"})
    assert response.status_code == 404


def test_invalid_import_gives_400(client: TestClient) -> None:
    session = new_session(client)
    response = client.post(f"/api/session/{session}/import", json={"xhtml": "<p>no math</p>"})
    assert response.status_code == 400
