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

from collections.abc import Callable, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol, cast

from disvimat.core.document import Node
from disvimat.core.transcription.braille import unicode_to_ascii

#: Module names the Python binding is published under, in order of
#: preference. The NVDA add-on ships it as ``libmathcat_py``.
MODULE_NAMES: tuple[str, ...] = ("libmathcat_py", "libmathcat")

#: Languages MathCAT speaks. Anything else falls back to our label tables;
#: French is notably absent.
SPEECH_LANGUAGES = frozenset({"en", "de", "es", "fi", "id", "no", "sv", "vi", "zh"})

#: Braille code to request per language. Only mappings we are confident
#: about are listed; an unlisted language keeps the table transcriber.
BRAILLE_CODES: dict[str, str] = {
    "es": "CMU",  # Código Matemático Unificado
    "en": "UEB",  # Unified English Braille (technical)
}

#: Default speech style; MathCAT also offers "SimpleSpeak" and "MathSpeak".
DEFAULT_SPEECH_STYLE = "ClearSpeak"


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


def is_available(module_names: Sequence[str] = MODULE_NAMES) -> bool:
    """Whether the MathCAT binding can be imported."""
    try:
        load_library(module_names)
    except MathCATUnavailable:
        return False
    return True


class MathCATBackend:
    """Speech and braille from MathCAT, driven by our own MathML.

    Satisfies both :class:`~disvimat.core.output.ExpressionReader` and
    :class:`~disvimat.core.output.BrailleProvider`.
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
        if rules_dir is not None:
            self._library.SetRulesDir(str(rules_dir))
        self._library.SetPreference("Language", language)
        self._library.SetPreference("SpeechStyle", speech_style)
        if self.braille_code:
            self._library.SetPreference("BrailleCode", self.braille_code)

    @property
    def supports_braille(self) -> bool:
        """Whether a braille code is known for this language."""
        return self.braille_code is not None

    # --- output ports ---------------------------------------------------------

    def read(self, nodes: list[Node]) -> str:
        self._load(nodes)
        return self._library.GetSpokenText().strip()

    def unicode(self, nodes: list[Node]) -> str:
        self._load(nodes)
        return self._library.GetBraille("")

    def ascii(self, nodes: list[Node]) -> str:
        return unicode_to_ascii(self.unicode(nodes))

    # --- internals ------------------------------------------------------------

    def _load(self, nodes: list[Node]) -> None:
        self._library.SetMathML(self._mathml_of(nodes))
