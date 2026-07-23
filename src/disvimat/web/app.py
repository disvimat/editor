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

from disvimat.backends import create_outputs
from disvimat.core.dvm import DvmError, from_dvm, to_dvm
from disvimat.core.editor import Editor, Result, create_editor
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.core.tables import Catalog, data_dir
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


class OpenRequest(BaseModel):
    dvm: str


class _Session:
    """Editor and export helpers of one user session."""

    def __init__(self, language: str, profile: str | None, keymap: str | None = None) -> None:
        self.language = language
        catalog = Catalog.load(data_dir() / "elements.json")
        # MathCAT when available, our tables otherwise; braille stays
        # unavailable rather than serving another language's braille.
        outputs = create_outputs(catalog, language)
        self.editor: Editor = create_editor(
            language=language, profile=profile, reader=outputs.reader, keymap=keymap
        )
        self.exporter = XHTMLExporter(self.editor.catalog)
        self.transcriber = outputs.braille

    def mathml(self) -> str:
        # One <math> per document line, so multi-line documents render whole.
        return "<br/>".join(
            ET.tostring(self.exporter.mathml(line), encoding="unicode")
            for line in self.editor.document.lines
        )

    def braille(self) -> str:
        assert self.transcriber is not None
        return "\n".join(self.transcriber.unicode(line) for line in self.editor.document.lines)


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
    default_keymap = os.environ.get("DISVIMAT_KEYMAP")

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
    def new_session(
        language: str | None = None, profile: str | None = None, keymap: str | None = None
    ) -> View:
        session_id = uuid.uuid4().hex
        session = _Session(
            language=language or default_language,
            profile=profile,
            keymap=keymap or default_keymap,
        )
        sessions[session_id] = session
        return view(session_id, session, session.editor.state())

    @app.post("/api/session/{session_id}/key", response_model=View)
    def key(session_id: str, request: KeyRequest) -> View:
        session = get_session(session_id)
        result: Result | None = None
        if request.keys:
            result = session.editor.press(request.keys)
        # The second stroke of a chord ("Ctrl+G, P") arrives as a bare
        # character; while a chord waits, resolve it as a key stroke
        # (bindings name letters in upper case) rather than typing it.
        if result is None and request.character and session.editor.chord_pending():
            result = session.editor.press(request.character.upper())
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
        content = session.exporter.xhtml_document_lines(
            session.editor.document.lines, language=session.language
        )
        return _download(content, "document.xhtml", "application/xhtml+xml")

    @app.get("/api/session/{session_id}/export.brl")
    def export_braille(session_id: str) -> PlainTextResponse:
        session = get_session(session_id)
        if session.transcriber is None:
            raise HTTPException(
                status_code=409,
                detail=f"no braille source for language {session.language!r}",
            )
        # Unicode braille (U+2800…), the modern portable form.
        return _download(session.braille() + "\n", "document.brl", "text/plain; charset=utf-8")

    @app.get("/api/session/{session_id}/export.dvm")
    def export_dvm(session_id: str) -> PlainTextResponse:
        session = get_session(session_id)
        content = to_dvm(session.editor.document.lines, language=session.language)
        return _download(content, "document.dvm", "application/json; charset=utf-8")

    @app.post("/api/session/{session_id}/open", response_model=View)
    def open_dvm(session_id: str, request: OpenRequest) -> View:
        session = get_session(session_id)
        try:
            document = from_dvm(request.dvm)
        except DvmError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return view(session_id, session, session.editor.load_lines(document.lines))

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
