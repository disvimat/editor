"""MathCAT adapter and the MathCAT-or-tables choice.

The real MathCAT binding is not on PyPI and has to be built from Rust, so
these tests drive the adapter with a fake library that records the calls.
That verifies everything on our side of the boundary — preferences,
MathML hand-off, braille conversion and the fallback policy — while the
real binding stays an integration step (see docs/en/MATHCAT.md).
"""

from pathlib import Path

import pytest

from disvimat.backends import create_outputs
from disvimat.core.document import Character, Node, Sign, Structure
from disvimat.core.editor import create_editor
from disvimat.core.mathcat import (
    MathCATBackend,
    MathCATUnavailable,
    is_available,
    load_library,
)
from disvimat.core.tables import Catalog

DATA = Path(__file__).resolve().parents[1] / "data"


class FakeMathCAT:
    """Stand-in for the MathCAT Python binding, recording what it is told."""

    def __init__(self, speech: str = "one plus two", braille: str = "⠼⠁⠖⠼⠃") -> None:
        self.preferences: dict[str, str] = {}
        self.rules_dir: str | None = None
        self.mathml: str | None = None
        self._speech = speech
        self._braille = braille

    def SetRulesDir(self, directory: str) -> None:  # noqa: N802
        self.rules_dir = directory

    def SetPreference(self, name: str, value: str) -> None:  # noqa: N802
        self.preferences[name] = value

    def SetMathML(self, mathml: str) -> None:  # noqa: N802
        self.mathml = mathml

    def GetSpokenText(self) -> str:  # noqa: N802
        return f"  {self._speech}  "  # MathCAT pads; the adapter must strip

    def GetBraille(self, node_id: str) -> str:  # noqa: N802
        return self._braille


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


def expression() -> list[Node]:
    return [Character("1"), Sign("plus"), Character("2")]


def mathml_of(nodes: list[Node]) -> str:
    return "<math><mn>1</mn></math>"


# --- the adapter ------------------------------------------------------------


def test_spanish_asks_for_the_cmu_braille_code() -> None:
    library = FakeMathCAT()
    backend = MathCATBackend(mathml_of, "es", library=library)
    assert library.preferences["Language"] == "es"
    assert library.preferences["BrailleCode"] == "CMU"
    assert library.preferences["SpeechStyle"] == "ClearSpeak"
    assert backend.supports_braille


def test_english_asks_for_ueb() -> None:
    library = FakeMathCAT()
    MathCATBackend(mathml_of, "en", library=library)
    assert library.preferences["BrailleCode"] == "UEB"


def test_rules_dir_is_passed_when_given(tmp_path: Path) -> None:
    library = FakeMathCAT()
    MathCATBackend(mathml_of, "es", library=library, rules_dir=tmp_path)
    assert library.rules_dir == str(tmp_path)


def test_reading_hands_over_our_mathml_and_strips_the_answer(catalog: Catalog) -> None:
    library = FakeMathCAT(speech="1 plus 2")
    backend = MathCATBackend(mathml_of, "es", library=library)
    assert backend.read(expression()) == "1 plus 2"
    assert library.mathml == "<math><mn>1</mn></math>"


def test_braille_comes_through_and_ascii_is_converted() -> None:
    library = FakeMathCAT(braille="⠼⠁⠖⠼⠃")
    backend = MathCATBackend(mathml_of, "es", library=library)
    assert backend.unicode(expression()) == "⠼⠁⠖⠼⠃"
    assert backend.ascii(expression()) == "#a6#b"


def test_a_language_mathcat_does_not_speak_is_refused() -> None:
    """French is not among MathCAT's languages: it must fall back to us."""
    with pytest.raises(MathCATUnavailable, match="does not speak"):
        MathCATBackend(mathml_of, "fr", library=FakeMathCAT())


def test_missing_library_is_reported_clearly() -> None:
    with pytest.raises(MathCATUnavailable, match="not installed"):
        load_library(["no_such_mathcat_module"])
    assert not is_available(["no_such_mathcat_module"])


# --- choosing the backend ---------------------------------------------------


def test_mathcat_leads_when_available(catalog: Catalog) -> None:
    outputs = create_outputs(catalog, "es", directory=DATA, library=FakeMathCAT())
    assert outputs.speech_backend == "mathcat"
    assert outputs.braille_backend == "mathcat"
    assert outputs.braille is not None
    assert outputs.braille.ascii(expression()) == "#a6#b"


def test_tables_take_over_when_mathcat_is_absent(catalog: Catalog) -> None:
    outputs = create_outputs(catalog, "es", directory=DATA, prefer_mathcat=False)
    assert outputs.speech_backend == "tables"
    assert outputs.braille_backend == "tables"
    assert outputs.reader is None  # the editor uses its own label tables
    assert outputs.braille is not None
    assert outputs.braille.ascii(expression()) == "#a6#b"


def test_french_keeps_our_tables_and_has_no_braille(catalog: Catalog) -> None:
    outputs = create_outputs(catalog, "fr", directory=DATA, library=FakeMathCAT())
    assert outputs.speech_backend == "tables"  # MathCAT has no French
    assert outputs.braille_backend == "none"  # and we have no French braille
    assert outputs.braille is None


def test_editor_reads_the_line_through_mathcat(catalog: Catalog) -> None:
    """Reading the line uses MathCAT; editing feedback stays ours."""
    outputs = create_outputs(catalog, "es", directory=DATA, library=FakeMathCAT(speech="1 más 2"))
    editor = create_editor(DATA, language="es", reader=outputs.reader)
    editor.type_character("1")
    feedback = editor.press("+")
    assert feedback is not None
    assert feedback.speech == "más"  # our label table, not MathCAT

    line = editor.press("Ctrl+Shift+L")
    assert line is not None
    assert line.speech == "1 más 2"  # MathCAT


def test_structures_reach_mathcat_as_mathml(catalog: Catalog) -> None:
    """The backend must receive real MathML built from the document tree."""
    from disvimat.export.xhtml import XHTMLExporter

    library = FakeMathCAT()
    backend = MathCATBackend(XHTMLExporter(catalog).mathml_text, "es", library=library)
    backend.read([Structure("fraction", [[Character("1")], [Character("2")]])])
    assert library.mathml is not None
    assert "<mfrac>" in library.mathml
