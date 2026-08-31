"""MathCAT adapter and the MathCAT-or-tables choice.

The real MathCAT binding is not on PyPI and is optional, so these tests
drive the adapter with a fake library that records the calls. That verifies
everything on our side of the boundary — preferences, MathML hand-off,
braille conversion and the fallback policy — regardless of whether MathCAT
is installed on the machine. See docs/en/MATHCAT.md and
scripts/install_mathcat.py.
"""

import threading
import time
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
#: Any existing directory serves as a stand-in rules dir for the fake tests,
#: so they never depend on a real MathCAT install being present.
RULES = DATA


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
    backend = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    assert library.preferences["Language"] == "es"
    assert library.preferences["BrailleCode"] == "CMU"
    assert library.preferences["SpeechStyle"] == "ClearSpeak"
    assert backend.supports_braille


def test_english_asks_for_ueb() -> None:
    library = FakeMathCAT()
    MathCATBackend(mathml_of, "en", library=library, rules_dir=RULES)
    assert library.preferences["BrailleCode"] == "UEB"


def test_rules_dir_is_passed_when_given(tmp_path: Path) -> None:
    library = FakeMathCAT()
    MathCATBackend(mathml_of, "es", library=library, rules_dir=tmp_path)
    assert library.rules_dir == str(tmp_path)


def test_reading_hands_over_our_mathml_and_strips_the_answer(catalog: Catalog) -> None:
    library = FakeMathCAT(speech="1 plus 2")
    backend = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    assert backend.read(expression()) == "1 plus 2"
    assert library.mathml == "<math><mn>1</mn></math>"


def test_braille_comes_through_and_ascii_is_converted() -> None:
    library = FakeMathCAT(braille="⠼⠁⠖⠼⠃")
    backend = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    assert backend.unicode(expression()) == "⠼⠁⠖⠼⠃"
    assert backend.ascii(expression()) == "#a6#b"


def test_a_language_we_keep_on_tables_is_refused() -> None:
    """French is kept on our tables (MathCAT's French rules are incomplete)."""
    with pytest.raises(MathCATUnavailable, match="does not speak"):
        MathCATBackend(mathml_of, "fr", library=FakeMathCAT(), rules_dir=RULES)


def test_missing_library_is_reported_clearly() -> None:
    with pytest.raises(MathCATUnavailable, match="not installed"):
        load_library(["no_such_mathcat_module"])
    assert not is_available(["no_such_mathcat_module"])


# --- choosing the backend ---------------------------------------------------


def test_mathcat_leads_when_available(catalog: Catalog) -> None:
    outputs = create_outputs(catalog, "es", directory=DATA, library=FakeMathCAT(), rules_dir=RULES)
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
    outputs = create_outputs(catalog, "fr", directory=DATA, library=FakeMathCAT(), rules_dir=RULES)
    assert outputs.speech_backend == "tables"  # French is kept on our tables
    assert outputs.braille_backend == "none"  # and we have no French braille
    assert outputs.braille is None


def test_editor_reads_the_line_through_mathcat(catalog: Catalog) -> None:
    """Reading the line uses MathCAT; editing feedback stays ours."""
    outputs = create_outputs(
        catalog, "es", directory=DATA, library=FakeMathCAT(speech="1 más 2"), rules_dir=RULES
    )
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
    backend = MathCATBackend(
        XHTMLExporter(catalog).mathml_text, "es", library=library, rules_dir=RULES
    )
    backend.read([Structure("fraction", [[Character("1")], [Character("2")]])])
    assert library.mathml is not None
    assert "<mfrac>" in library.mathml


# --- the shared library -----------------------------------------------------
#
# MathCAT is a module, so there is one per process and its preferences are
# global. Every web session builds its own backend against that one library,
# so the adapter has to claim it per call. These tests use a fake that
# answers according to whatever preferences are set *at the moment of the
# call*, exactly as the real library does — a fake that merely recorded the
# last value written could not tell the two behaviours apart.


class SharedMathCAT:
    """One process-wide library, answering from its current preferences."""

    def __init__(self, delay: float = 0.0) -> None:
        self.preferences: dict[str, str] = {}
        self.mathml: str | None = None
        self._delay = delay

    def SetRulesDir(self, directory: str) -> None:  # noqa: N802
        pass

    def SetPreference(self, name: str, value: str) -> None:  # noqa: N802
        self.preferences[name] = value

    def SetMathML(self, mathml: str) -> None:  # noqa: N802
        self.mathml = mathml
        # Real MathCAT does actual work here and releases the GIL while it
        # does; this is where another thread gets in.
        if self._delay:
            time.sleep(self._delay)

    def GetSpokenText(self) -> str:  # noqa: N802
        return f"speech:{self.preferences['Language']}"

    def GetBraille(self, node_id: str) -> str:  # noqa: N802
        return f"braille:{self.preferences['BrailleCode']}"


def test_a_second_session_does_not_steal_the_first_one_s_language() -> None:
    library = SharedMathCAT()
    spanish = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    english = MathCATBackend(mathml_of, "en", library=library, rules_dir=RULES)

    assert english.read(expression()) == "speech:en"
    assert spanish.read(expression()) == "speech:es"
    assert english.read(expression()) == "speech:en"


def test_braille_never_comes_back_in_another_country_s_code() -> None:
    """The severe half: CMU and UEB are different notations, not dialects.

    A Spanish reader handed UEB gets wrong braille presented as right,
    which is the one thing docs/*/BRAILLE.md promises cannot happen.
    """
    library = SharedMathCAT()
    spanish = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    english = MathCATBackend(mathml_of, "en", library=library, rules_dir=RULES)

    assert english.unicode(expression()) == "braille:UEB"
    assert spanish.unicode(expression()) == "braille:CMU"
    assert spanish.ascii(expression()) is not None  # goes through unicode()
    assert english.unicode(expression()) == "braille:UEB"


def test_sessions_in_different_languages_may_read_at_the_same_time() -> None:
    """Web endpoints are synchronous, so FastAPI runs them in a thread pool."""
    library = SharedMathCAT(delay=0.001)
    backends = {
        "es": MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES),
        "en": MathCATBackend(mathml_of, "en", library=library, rules_dir=RULES),
        "de": MathCATBackend(mathml_of, "de", library=library, rules_dir=RULES),
    }
    wrong: list[str] = []

    def hammer(language: str) -> None:
        backend = backends[language]
        for _ in range(20):
            spoken = backend.read(expression())
            if spoken != f"speech:{language}":
                wrong.append(f"{language} was handed {spoken}")

    threads = [
        threading.Thread(target=hammer, args=(language,)) for language in backends for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not wrong, f"{len(wrong)} readings came back in the wrong language: {wrong[:3]}"


class ThreadLocalMathCAT(SharedMathCAT):
    """A fake that keeps its rules per thread, as the real library does.

    ``SetRulesDir`` on one thread does not make the preferences exist on
    another: there, ``SetPreference`` fails outright. A server answers from
    a pool of threads, so a backend built on one and used on another must
    still work. The earlier fake could not tell the two behaviours apart,
    and the real bug — a 500 on braille export — went unseen because the
    suite runs with MathCAT switched off.
    """

    def __init__(self, delay: float = 0.0) -> None:
        super().__init__(delay)
        self._local = threading.local()

    def SetRulesDir(self, directory: str) -> None:  # noqa: N802
        self._local.rules = directory

    def SetPreference(self, name: str, value: str) -> None:  # noqa: N802
        if getattr(self._local, "rules", None) is None:
            raise OSError(f"{name} is an unknown MathCAT preference!")
        super().SetPreference(name, value)


def test_a_backend_built_on_one_thread_works_on_another() -> None:
    library = ThreadLocalMathCAT()
    backend = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    assert backend.read(expression()) == "speech:es"  # this thread is set up

    answers: list[str] = []
    failures: list[str] = []

    def elsewhere() -> None:
        try:
            answers.append(backend.read(expression()))
            answers.append(backend.unicode(expression()))
        except Exception as error:  # noqa: BLE001 - the point of the test
            failures.append(f"{type(error).__name__}: {error}")

    thread = threading.Thread(target=elsewhere)
    thread.start()
    thread.join()

    assert not failures, f"the backend broke on another thread: {failures}"
    assert answers == ["speech:es", "braille:CMU"]


def test_every_thread_of_a_pool_gets_its_own_rules() -> None:
    """Which is what a synchronous FastAPI endpoint runs in."""
    library = ThreadLocalMathCAT(delay=0.001)
    spanish = MathCATBackend(mathml_of, "es", library=library, rules_dir=RULES)
    english = MathCATBackend(mathml_of, "en", library=library, rules_dir=RULES)
    wrong: list[str] = []

    def hammer(backend: MathCATBackend, language: str) -> None:
        for _ in range(10):
            try:
                spoken = backend.read(expression())
            except Exception as error:  # noqa: BLE001
                wrong.append(f"{language}: {type(error).__name__}: {error}")
                return
            if spoken != f"speech:{language}":
                wrong.append(f"{language} was handed {spoken}")

    threads = [
        threading.Thread(target=hammer, args=(backend, language))
        for backend, language in ((spanish, "es"), (english, "en"))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not wrong, wrong[:3]
