"""Optional MathCAT backend for speech and braille.

`MathCAT <https://daisy.github.io/MathCAT/>`_ (DAISY, MIT licence) turns
MathML into speech and braille. It reads MathML, which is exactly what
this project already produces, so it plugs into the
:mod:`disvimat.core.output` ports without touching the document, the
keyboard or the calculator.

**Why it matters here.** MathCAT implements *CMU* (Código Matemático
Unificado), the Spanish mathematical braille standard, maintained by
braille specialists. Our own ``br6`` tables are explicitly provisional, so
where MathCAT is available its braille is the one to trust.

**What it does not cover.** MathCAT reads mathematical *notation*; it does
not produce the editor's own feedback ("blank 2", "exit structure:
fraction"), which stays in the label tables. It also has no French, so
French keeps using our tables.

**Availability.** MathCAT is not published on PyPI: the Python binding is
built from the Rust sources (see the integration notes in the docs). This
module therefore never imports it at module load time; everything degrades
to the table-driven engines when the library is absent.
"""

import os
import threading
from collections.abc import Callable, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from disvimat.core.document import Node
from disvimat.core.transcription.braille import unicode_to_ascii

#: Module names the Python binding is published under, in order of
#: preference. The NVDA add-on ships it as ``libmathcat_py``.
MODULE_NAMES: tuple[str, ...] = ("libmathcat_py", "libmathcat")

#: Languages MathCAT speaks (its ``Rules/Languages`` directories). Anything
#: else falls back to our label tables. French *is* present, but its rules
#: are incomplete (they still fall back to English for many expressions),
#: so we keep French on our own tables for now — see ``docs/*/MATHCAT.md``.
SPEECH_LANGUAGES = frozenset({"en", "de", "es", "fi", "id", "nb", "ru", "sv", "vi", "zh"})

#: Braille code to request per language. Only mappings we are confident
#: about are listed; an unlisted language keeps the table transcriber.
BRAILLE_CODES: dict[str, str] = {
    "es": "CMU",  # Código Matemático Unificado
    "en": "UEB",  # Unified English Braille (technical)
}

#: Default speech style; MathCAT also offers "SimpleSpeak" and "MathSpeak".
DEFAULT_SPEECH_STYLE = "ClearSpeak"

#: Environment variable pointing at MathCAT's ``Rules`` directory.
RULES_DIR_ENV = "MATHCAT_RULES_DIR"

#: Serialises every use of the MathCAT binding. The binding is a module —
#: one per process — and its preferences are shared, so two backends in
#: different languages would otherwise take the settings from each other.
_LIBRARY_LOCK = threading.RLock()

#: Which library and rules directory this thread has been pointed at.
#:
#: MathCAT keeps its state **per thread**: ``SetRulesDir`` on one thread
#: does not make the preferences exist on another, where ``SetPreference``
#: then fails with "Language is an unknown MathCAT preference". A server
#: answers requests from a pool of threads, so the rules have to be set on
#: whichever thread is asking, not once at construction.
_THREAD = threading.local()


class MathCATUnavailable(RuntimeError):
    """MathCAT cannot be used (not installed, or language unsupported)."""


class _Library(Protocol):
    """The subset of the MathCAT Python binding this adapter needs."""

    def SetRulesDir(self, directory: str) -> Any: ...  # noqa: N802
    def SetPreference(self, name: str, value: str) -> Any: ...  # noqa: N802
    def SetMathML(self, mathml: str) -> Any: ...  # noqa: N802
    def GetSpokenText(self) -> str: ...  # noqa: N802
    def GetBraille(self, node_id: str) -> str: ...  # noqa: N802


def load_library(module_names: Sequence[str] = MODULE_NAMES) -> _Library:
    """Import the MathCAT binding, or raise :class:`MathCATUnavailable`."""
    for name in module_names:
        try:
            return cast(_Library, import_module(name))
        except ImportError:
            continue
    raise MathCATUnavailable(
        f"the MathCAT Python binding is not installed (tried: {', '.join(module_names)})"
    )


def find_rules_dir(module_names: Sequence[str] = MODULE_NAMES) -> Path | None:
    """Locate MathCAT's ``Rules`` directory.

    MathCAT keeps its speech and braille rules in an external ``Rules``
    directory, and :meth:`SetRulesDir` must be its first call. We look, in
    order, at the ``MATHCAT_RULES_DIR`` environment variable and at a
    ``Rules`` folder next to the imported binding.
    """
    from_environment = os.environ.get(RULES_DIR_ENV)
    if from_environment and Path(from_environment).is_dir():
        return Path(from_environment)
    try:
        library = load_library(module_names)
    except MathCATUnavailable:
        return None
    module_file = getattr(library, "__file__", None)
    if module_file:
        candidate = Path(module_file).resolve().parent / "Rules"
        if candidate.is_dir():
            return candidate
    return None


def is_available(module_names: Sequence[str] = MODULE_NAMES) -> bool:
    """Whether the binding can be imported and its rules can be located."""
    try:
        load_library(module_names)
    except MathCATUnavailable:
        return False
    return find_rules_dir(module_names) is not None


class MathCATBackend:
    """Speech and braille from MathCAT, driven by our own MathML.

    Satisfies both :class:`~disvimat.core.output.ExpressionReader` and
    :class:`~disvimat.core.output.BrailleProvider`.

    **The library is shared, its settings are global.** MathCAT is a
    module, so there is one of it per process, and ``SetPreference`` writes
    settings that belong to nobody in particular. On the desktop that is
    harmless — one process, one reader. On the web, where every session
    builds its own backend, the last session to be created used to take the
    language away from all the others: a Spanish reader would be handed
    English speech and UEB braille as soon as anyone opened an English
    session, silently, which is exactly what this project promises never
    happens (see ``docs/*/BRAILLE.md``).

    So a backend owns no state inside the library. It claims it instead:
    every call re-applies its own preferences and reads the answer without
    letting go of :data:`_LIBRARY_LOCK` in between. Re-applying costs
    0.0012 ms against 0.22 ms for the reading itself, so the simple and
    obviously correct arrangement is also cheap enough not to matter.
    """

    def __init__(
        self,
        mathml_of: Callable[[list[Node]], str],
        language: str,
        *,
        library: _Library | None = None,
        rules_dir: Path | None = None,
        braille_code: str | None = None,
        speech_style: str = DEFAULT_SPEECH_STYLE,
    ) -> None:
        if language not in SPEECH_LANGUAGES:
            raise MathCATUnavailable(f"MathCAT does not speak {language!r}")
        self._mathml_of = mathml_of
        self.language = language
        self.braille_code = braille_code or BRAILLE_CODES.get(language)
        self._library: _Library = library if library is not None else load_library()
        # SetRulesDir MUST be the first call (besides GetVersion): the rules
        # define which preferences and languages exist. Without them every
        # SetPreference raises, so a missing rules directory means MathCAT is
        # unavailable and the caller falls back to the tables.
        rules = rules_dir or find_rules_dir()
        if rules is None:
            raise MathCATUnavailable("MathCAT rules directory not found")
        self._speech_style = speech_style
        self._rules = str(rules)
        with _LIBRARY_LOCK:
            self._claim()

    @property
    def supports_braille(self) -> bool:
        """Whether a braille code is known for this language."""
        return self.braille_code is not None

    # --- output ports ---------------------------------------------------------

    def read(self, nodes: list[Node]) -> str:
        mathml = self._mathml_of(nodes)  # our own work: no need for the lock
        with _LIBRARY_LOCK:
            self._claim()
            self._library.SetMathML(mathml)
            return self._library.GetSpokenText().strip()

    def unicode(self, nodes: list[Node]) -> str:
        mathml = self._mathml_of(nodes)
        with _LIBRARY_LOCK:
            self._claim()
            self._library.SetMathML(mathml)
            return self._library.GetBraille("")

    def ascii(self, nodes: list[Node]) -> str:
        return unicode_to_ascii(self.unicode(nodes))

    # --- internals ------------------------------------------------------------

    def _claim(self) -> None:
        """Point the library at this backend's language, on this thread.

        Whoever configured it last does not matter: these settings decide
        the answer, so they are written again every time, with the lock
        held from here until the answer has been read back.

        ``SetRulesDir`` comes first on a thread that has not seen it,
        because the rules are what define which preferences exist, and
        MathCAT holds them per thread.
        """
        # Which library, not just which directory: the tests drive fakes,
        # and a stale mark would skip the call one of them still needs.
        configured = (self._library, self._rules)
        if getattr(_THREAD, "configured", None) != configured:
            self._library.SetRulesDir(self._rules)
            _THREAD.configured = configured
        self._library.SetPreference("Language", self.language)
        self._library.SetPreference("SpeechStyle", self._speech_style)
        if self.braille_code:
            self._library.SetPreference("BrailleCode", self.braille_code)
