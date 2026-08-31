"""The editor as one object a front end can drive.

The FastAPI endpoints and the browser want exactly the same operations:
press a key, open a document, hand one back. Written twice they would
drift, the way the two keyboard mappings did, so they are written once
here and both front ends call them.

**Everything crosses as JSON.** Each method returns a string rather than an
object. Over HTTP that is what went over the wire anyway; under Pyodide it
means one string crosses from WebAssembly into JavaScript, with no object
graph to marshal and no proxy to remember to free. It costs a
``json.dumps`` of a few hundred bytes per key stroke, which is nothing
beside the work that produced it.

This module knows nothing about HTTP or about the browser, so the same
object serves a server, a tab with no server at all, and the tests.
"""

import json
import xml.etree.ElementTree as ET

from disvimat.backends import Workspace, create_workspace, open_document
from disvimat.core.dvm import DvmError, to_dvm
from disvimat.core.editor import Result
from disvimat.core.filters.mathml import FilterError, MathMLFilter
from disvimat.export.xhtml import XHTMLExporter

#: The formats a document can be handed back in.
EXPORTS = ("dvm", "xhtml", "brl")


class BridgeError(Exception):
    """Something the user did cannot be done, with a reason to tell them."""


class Bridge:
    """One open document, and the operations a front end performs on it."""

    def __init__(
        self,
        language: str = "en",
        profile: str | None = None,
        keymap: str | None = None,
    ) -> None:
        self._keymap = keymap
        self._adopt(create_workspace(language=language, profile=profile, keymap=keymap))

    # --- operations -----------------------------------------------------------

    def state(self) -> str:
        """The current view, without doing anything."""
        return self._view(self._workspace.editor.state())

    def press(self, keys: str | None = None, character: str | None = None) -> str:
        """Apply a canonical stroke, a printable character, or both.

        The page sends both when a printable key might also be a sign: ``+``
        is a catalogue sign before it is a character. The second stroke of a
        chord arrives bare and is resolved as a stroke while one is pending,
        rather than being typed.
        """
        editor = self._workspace.editor
        result: Result | None = None
        if keys:
            result = editor.press(keys)
        if result is None and character and editor.chord_pending():
            result = editor.press(character.upper())
        if result is None and character:
            result = editor.type_character(character)
        return self._view(result if result is not None else editor.state())

    def open(self, dvm: str) -> str:
        """Open a ``.dvm`` under the language and profile it declares.

        This is what applies an exam file's restrictions: the document is
        not poured into the running editor, it builds the one it asks for.
        """
        try:
            self._adopt(open_document(dvm, keymap=self._keymap))
        except DvmError as error:
            raise BridgeError(str(error)) from error
        return self.state()

    def import_xhtml(self, xhtml: str) -> str:
        """Replace the content with an imported XHTML document (D1)."""
        try:
            nodes = MathMLFilter(self._workspace.editor.catalog).from_xhtml(xhtml)
        except FilterError as error:
            raise BridgeError(str(error)) from error
        return self._view(self._workspace.editor.load(nodes))

    def export(self, what: str) -> str:
        """The whole document in one of :data:`EXPORTS`."""
        document = self._workspace.editor.document
        if what == "dvm":
            # The profile travels with the document, so an exam saved here
            # is still an exam when it is opened again.
            return to_dvm(
                document.lines,
                language=self._workspace.language,
                profile=self._workspace.profile,
            )
        if what == "xhtml":
            return self._exporter.xhtml_document_lines(
                document.lines, language=self._workspace.language
            )
        if what == "brl":
            braille = self._workspace.braille
            if braille is None:
                raise BridgeError(f"no braille source for language {self._workspace.language!r}")
            # Unicode braille (U+2800…), the modern portable form.
            return "\n".join(braille.unicode(line) for line in document.lines) + "\n"
        raise BridgeError(f"unknown export format: {what!r}")

    # --- internals ------------------------------------------------------------

    def _adopt(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._exporter = XHTMLExporter(workspace.editor.catalog)
        # Rendered MathML per line revision (see Document.revisions): only
        # the edited line can have changed, so the rest is served from here
        # and a key stroke costs the same in a long document as in a short.
        self._mathml_cache: dict[int, str] = {}

    def _mathml(self) -> str:
        """One ``<math>`` per line, so a multi-line document renders whole."""
        document = self._workspace.editor.document
        revisions = document.revisions()
        rendered = []
        for revision, line in zip(revisions, document.lines, strict=True):
            mathml = self._mathml_cache.get(revision)
            if mathml is None:
                mathml = ET.tostring(self._exporter.mathml(line), encoding="unicode")
                self._mathml_cache[revision] = mathml
            rendered.append(mathml)
        # Revisions are never reused, so entries for superseded lines would
        # pile up: drop the ones no line claims any more.
        if len(self._mathml_cache) > len(revisions):
            live = set(revisions)
            self._mathml_cache = {r: m for r, m in self._mathml_cache.items() if r in live}
        return "<br/>".join(rendered)

    def _view(self, result: Result) -> str:
        return json.dumps(
            {
                "text": result.text,
                "position": result.position,
                "speech": result.speech,
                "mathml": self._mathml(),
            }
        )
