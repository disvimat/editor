"""DISVIMAT web application (FastAPI).

Keeps one editing session per user (a core :class:`Editor` in memory) and
exposes the same operations as the desktop version: pressing keys,
typing characters, importing and exporting. The visual presentation is
native MathML, which modern browsers speak; on top of that every answer
carries the core speech string, announced in an ``aria-live`` region.
"""

import os
import re
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from collections import OrderedDict
from collections.abc import Callable
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

#: Seconds a session survives without requests. A session holds a whole
#: document in memory, so it cannot be kept for ever: with no bound, every
#: page ever opened leaks until the process restarts.
DEFAULT_SESSION_TTL = 2 * 60 * 60.0
#: Most sessions kept at once; past it the least recently used is dropped.
DEFAULT_MAX_SESSIONS = 500


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
        # Rendered MathML per line revision (see Document.revisions).
        self._mathml_cache: dict[int, str] = {}

    def mathml(self) -> str:
        """One ``<math>`` per document line, so multi-line documents render whole.

        Every key stroke re-sends the whole document to the page, but only
        the edited line can have changed, so the rest is served from the
        cache. Without this the cost of a key stroke grows with the length
        of the document; with it, it stays flat.
        """
        document = self.editor.document
        revisions = document.revisions()
        rendered = []
        for revision, line in zip(revisions, document.lines, strict=True):
            mathml = self._mathml_cache.get(revision)
            if mathml is None:
                mathml = ET.tostring(self.exporter.mathml(line), encoding="unicode")
                self._mathml_cache[revision] = mathml
            rendered.append(mathml)
        # Revisions are never reused, so entries for deleted lines (and for
        # every line superseded by an edit) would pile up: drop them.
        if len(self._mathml_cache) > len(revisions):
            live = set(revisions)
            self._mathml_cache = {r: m for r, m in self._mathml_cache.items() if r in live}
        return "<br/>".join(rendered)

    def braille(self) -> str:
        assert self.transcriber is not None
        return "\n".join(self.transcriber.unicode(line) for line in self.editor.document.lines)


class _SessionStore:
    """The live sessions, bounded in both age and number.

    Sessions live in memory, so two things have to hold: an abandoned
    session must disappear on its own (``ttl``), and a burst of new ones
    must not grow without limit (``max_sessions``, least recently used
    discarded first). Both are enforced here, so the endpoints only ever
    ask for a session by id.

    The endpoints are synchronous, which means FastAPI runs them in a
    thread pool and several can reach the store at once; each method takes
    a lock. The lock guards the *store* — which sessions exist — not the
    editing of any one session.
    """

    def __init__(
        self,
        ttl: float = DEFAULT_SESSION_TTL,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl
        self._max = max(1, max_sessions)
        self._clock = clock
        # Ordered by last use: the first entry is the least recently used.
        self._sessions: OrderedDict[str, tuple[float, _Session]] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def add(self, session_id: str, session: _Session) -> None:
        with self._lock:
            self._drop_expired()
            while len(self._sessions) >= self._max:
                self._sessions.popitem(last=False)
            self._sessions[session_id] = (self._clock(), session)

    def get(self, session_id: str) -> _Session | None:
        """The session, with its deadline refreshed; ``None`` when gone."""
        with self._lock:
            self._drop_expired()
            entry = self._sessions.get(session_id)
            if entry is None:
                return None
            self._sessions[session_id] = (self._clock(), entry[1])
            self._sessions.move_to_end(session_id)
            return entry[1]

    def _drop_expired(self) -> None:
        """Discard idle sessions. The caller holds the lock."""
        deadline = self._clock() - self._ttl
        expired = [key for key, (used, _) in self._sessions.items() if used <= deadline]
        for key in expired:
            del self._sessions[key]


def render_page(language: str) -> str:
    """The page with its ``{{placeholders}}`` replaced by the ui table."""
    text = UIText.load(language=language)
    template = (_STATIC / "index.html").read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return language if name == "language" else text(name)

    return _PLACEHOLDER.sub(replace, template)


def create_app(store: _SessionStore | None = None) -> FastAPI:
    """Build the application.

    Sessions are held in memory and expire when idle; ``store`` lets the
    tests supply their own clock and limits.
    """
    app = FastAPI(title="DISVIMAT web")
    if store is None:
        store = _SessionStore(
            ttl=float(os.environ.get("DISVIMAT_SESSION_TTL", DEFAULT_SESSION_TTL)),
            max_sessions=int(os.environ.get("DISVIMAT_MAX_SESSIONS", DEFAULT_MAX_SESSIONS)),
        )
    sessions = store
    default_language = os.environ.get("DISVIMAT_LANG", "en")
    default_keymap = os.environ.get("DISVIMAT_KEYMAP")

    def get_session(session_id: str) -> _Session:
        session = sessions.get(session_id)
        if session is None:
            # This also covers a session that simply timed out, which is
            # now an ordinary thing to happen. The page turns it into a new
            # session and says so out loud: a screen reader user must never
            # be left typing into an editor that has quietly stopped
            # answering.
            raise HTTPException(status_code=404, detail="unknown or expired session")
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
        sessions.add(session_id, session)
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
