"""DISVIMAT web application (FastAPI).

Keeps one editing session per user (a core :class:`Editor` in memory) and
exposes the same operations as the desktop version: pressing keys,
typing characters, importing and exporting. The visual presentation is
native MathML, which modern browsers speak; on top of that every answer
carries the core speech string, announced in an ``aria-live`` region.
"""

import os
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from disvimat.core.editor import Editor, Result, create_editor
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.transcription.braille import (
    BrailleTablesMissing,
    BrailleTranscriber,
    create_transcriber,
)
from disvimat.core.ui_text import UIText
from disvimat.export.xhtml import XHTMLExporter

_STATIC = Path(__file__).resolve().parent / "static"
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class View(BaseModel):
    """What the page needs in order to reflect the editor state."""

    session: str
    text: str
    position: int
    speech: str
    mathml: str


class KeyRequest(BaseModel):
    """A key from the page: canonical stroke and/or printable character."""

    keys: str | None = None
    character: str | None = None


class ImportRequest(BaseModel):
    xhtml: str


class _Session:
    """Editor and export helpers of one user session."""

    def __init__(self, language: str, profile: str | None) -> None:
        self.language = language
        self.editor: Editor = create_editor(language=language, profile=profile)
        self.exporter = XHTMLExporter(self.editor.catalog)
        try:
            self.transcriber: BrailleTranscriber | None = create_transcriber(language=language)
        except BrailleTablesMissing:
            # No braille tables for this language: braille stays unavailable
            # rather than silently serving another language's braille.
            self.transcriber = None

    def mathml(self) -> str:
        element = self.exporter.mathml(self.editor.document.root)
        return ET.tostring(element, encoding="unicode")


def render_page(language: str) -> str:
    """The page with its ``{{placeholders}}`` replaced by the ui table."""
    text = UIText.load(language=language)
    template = (_STATIC / "index.html").read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return language if name == "language" else text(name)

    return _PLACEHOLDER.sub(replace, template)


def create_app() -> FastAPI:
    """Build the application; sessions live as long as the process."""
    app = FastAPI(title="DISVIMAT web")
    sessions: dict[str, _Session] = {}
    default_language = os.environ.get("DISVIMAT_LANG", "en")

    def get_session(session_id: str) -> _Session:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="unknown session")
        return session

    def view(session_id: str, session: _Session, result: Result) -> View:
        return View(
            session=session_id,
            text=result.text,
            position=result.position,
            speech=result.speech,
            mathml=session.mathml(),
        )

    @app.get("/", response_class=HTMLResponse)
    def index(language: str | None = None) -> str:
        return render_page(language or default_language)

    @app.post("/api/session", response_model=View)
    def new_session(language: str | None = None, profile: str | None = None) -> View:
        session_id = uuid.uuid4().hex
        session = _Session(language=language or default_language, profile=profile)
        sessions[session_id] = session
        return view(session_id, session, session.editor.state())

    @app.post("/api/session/{session_id}/key", response_model=View)
    def key(session_id: str, request: KeyRequest) -> View:
        session = get_session(session_id)
        result: Result | None = None
        if request.keys:
            result = session.editor.press(request.keys)
        if result is None and request.character:
            result = session.editor.type_character(request.character)
        if result is None:
            result = session.editor.state()
        return view(session_id, session, result)

    @app.post("/api/session/{session_id}/import", response_model=View)
    def import_xhtml(session_id: str, request: ImportRequest) -> View:
        session = get_session(session_id)
        try:
            nodes = MathMLFilter(session.editor.catalog).from_xhtml(request.xhtml)
        except FilterError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return view(session_id, session, session.editor.load(nodes))

    def _download(content: str, name: str, media_type: str) -> PlainTextResponse:
        return PlainTextResponse(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    @app.get("/api/session/{session_id}/export.xhtml")
    def export_xhtml(session_id: str) -> PlainTextResponse:
        session = get_session(session_id)
        content = session.exporter.xhtml_document(
            session.editor.document.root, language=session.language
        )
        return _download(content, "document.xhtml", "application/xhtml+xml")

    @app.get("/api/session/{session_id}/export.bra")
    def export_bra(session_id: str) -> PlainTextResponse:
        session = get_session(session_id)
        if session.transcriber is None:
            raise HTTPException(
                status_code=409,
                detail=f"no braille tables for language {session.language!r}",
            )
        content = session.transcriber.ascii(session.editor.document.root) + "\n"
        return _download(content, "document.bra", "text/plain")

    @app.get("/favicon.ico")
    def favicon() -> FileResponse:
        return FileResponse(_STATIC / "favicon.svg", media_type="image/svg+xml")

    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
