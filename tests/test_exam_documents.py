"""The restrictions travel inside the document.

The teacher prepares an exam, hands over the file, and the student opens it
on whatever machine is to hand — another operating system, or a browser —
and finds the restrictions the file carries. That only works if opening a
``.dvm`` builds the editor the document asks for, rather than pouring its
lines into whatever editor happens to be running.

The format has always stored the language and the profile. Until now both
interfaces dropped them on the floor: an exam saved with the calculator
locked opened with the calculator working.
"""

import json

import pytest
from fastapi.testclient import TestClient

from disvimat.backends import create_workspace, open_document
from disvimat.core.dvm import DvmError, from_dvm, to_dvm
from disvimat.core.editor import Editor
from disvimat.web.app import create_app


def written(
    profile: str | None, language: str = "es", keys: tuple[str, ...] = ("1", "+", "2")
) -> str:
    """A document as a teacher would save it."""
    workspace = create_workspace(language=language, profile=profile)
    for key in keys:
        if workspace.editor.press(key) is None:
            workspace.editor.type_character(key)
    return to_dvm(
        workspace.editor.document.lines,
        language=workspace.language,
        profile=workspace.profile,
    )


def calculate(editor: Editor) -> str:
    result = editor.press("Ctrl+Return")
    assert result is not None
    return result.speech


# --- opening applies what the document declares ------------------------------


def test_an_exam_opens_with_its_calculator_locked() -> None:
    """The whole point: the lock is in the file, not in the machine."""
    workspace = open_document(written("exam"))
    assert workspace.profile == "exam"
    assert "3" not in calculate(workspace.editor), "the exam's lock was not applied"


def test_the_same_document_without_a_profile_calculates() -> None:
    """So the test above is about the profile, not about calculation failing."""
    workspace = open_document(written(None))
    assert "3" in calculate(workspace.editor)


def test_a_beginner_document_withholds_the_elements_above_its_level() -> None:
    """A7 is a level, not only a calculator switch."""
    workspace = open_document(written("beginner"))
    assert workspace.editor.press("Ctrl+M") is None, "a level 3 sign reached a level 1 document"
    assert workspace.editor.press("+") is not None


def test_an_unrestricted_document_offers_everything() -> None:
    workspace = open_document(written(None))
    assert workspace.editor.press("Ctrl+M") is not None


def test_the_document_language_governs_how_it_is_read() -> None:
    """Mathematical braille is normative: reading a Spanish document under
    an English editor would transcribe it into UEB instead of CMU."""
    assert open_document(written(None, language="es")).language == "es"
    assert open_document(written(None, language="en")).language == "en"


def test_a_profile_the_installation_does_not_know_is_a_malformed_document() -> None:
    payload = json.loads(written("exam"))
    payload["profile"] = "no_such_profile"
    with pytest.raises(DvmError, match="profile"):
        open_document(json.dumps(payload))


# --- and saving keeps them ---------------------------------------------------


def test_an_exam_saved_again_is_still_an_exam() -> None:
    """Otherwise the restriction lasts one sitting and then evaporates."""
    workspace = open_document(written("exam"))
    workspace.editor.type_character("7")
    saved = to_dvm(
        workspace.editor.document.lines,
        language=workspace.language,
        profile=workspace.profile,
    )
    assert from_dvm(saved).profile == "exam"
    assert "3" not in calculate(open_document(saved).editor)


# --- through the web adapter -------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def open_in_browser(client: TestClient, dvm: str) -> str:
    session = client.post("/api/session").json()["session"]
    response = client.post(f"/api/session/{session}/open", json={"dvm": dvm})
    assert response.status_code == 200, response.text
    return str(session)


def test_the_browser_applies_the_exam_it_is_given(client: TestClient) -> None:
    session = open_in_browser(client, written("exam"))
    answer = client.post(f"/api/session/{session}/key", json={"keys": "Ctrl+Return"})
    assert "3" not in answer.json()["speech"]


def test_the_browser_saves_the_profile_it_opened_under(client: TestClient) -> None:
    """A teacher preparing an exam in the browser used to save it without
    any profile at all, so it restricted nobody."""
    session = open_in_browser(client, written("exam"))
    saved = client.get(f"/api/session/{session}/export.dvm").text
    assert from_dvm(saved).profile == "exam"


def test_the_browser_rejects_a_document_it_cannot_honour(client: TestClient) -> None:
    payload = json.loads(written("exam"))
    payload["profile"] = "no_such_profile"
    session = client.post("/api/session").json()["session"]
    response = client.post(f"/api/session/{session}/open", json={"dvm": json.dumps(payload)})
    assert response.status_code == 400
    assert "profile" in response.json()["detail"]


def test_opening_a_document_does_not_leave_the_old_one_showing(client: TestClient) -> None:
    session = client.post("/api/session").json()["session"]
    client.post(f"/api/session/{session}/key", json={"keys": "9", "character": "9"})
    response = client.post(f"/api/session/{session}/open", json={"dvm": written(None)})
    assert response.json()["text"] == "1+2"
    assert "<mn>1</mn>" in response.json()["mathml"]
