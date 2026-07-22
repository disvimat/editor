"""liblouis text-braille adapter and its place in the braille ladder.

The real liblouis is a native library and may not be installed, so these
tests drive the adapter with a fake ``Liblouis`` that records the calls.
That covers our side of the boundary — table selection, linearisation and
ASCII conversion — regardless of whether liblouis is present. See
docs/en/BRAILLE.md and scripts/install_liblouis.py.
"""

from pathlib import Path

import pytest

from disvimat.backends import create_outputs
from disvimat.core.document import Character, Node, Sign
from disvimat.core.liblouis import Liblouis, LiblouisText, LiblouisUnavailable
from disvimat.core.tables import Catalog

DATA = Path(__file__).resolve().parents[1] / "data"


class FakeLiblouis:
    """Stand-in for the native binding, mapping a few chars to braille."""

    _CELLS = {"1": "⠼⠁", "2": "⠼⠃", "3": "⠼⠉", "+": "⠖", "a": "⠁", " ": "⠀"}

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def version(self) -> str:
        return "fake-3.38"

    def translate(self, table: str, text: str) -> str:
        self.calls.append((table, text))
        return "".join(self._CELLS.get(c, "⠿") for c in text)


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.load(DATA / "elements.json")


def expression() -> list[Node]:
    return [Character("1"), Sign("plus"), Character("2")]


def linearise(nodes: list[Node]) -> str:
    # a trivial lineariser standing in for the presenter
    out = ""
    for node in nodes:
        if isinstance(node, Character):
            out += node.text
        elif isinstance(node, Sign):
            out += "+" if node.element_id == "plus" else "?"
    return out


# --- the adapter ------------------------------------------------------------


def test_spanish_uses_the_official_table() -> None:
    native = FakeLiblouis()
    provider = LiblouisText(linearise, "es", native=native)  # type: ignore[arg-type]
    assert provider.unicode(expression()) == "⠼⠁⠖⠼⠃"
    assert native.calls[-1][0] == "es-g1.ctb"


def test_ascii_export_is_converted() -> None:
    native = FakeLiblouis()
    provider = LiblouisText(linearise, "es", native=native)  # type: ignore[arg-type]
    assert provider.ascii(expression()) == "#a6#b"


def test_language_without_a_table_is_refused() -> None:
    with pytest.raises(LiblouisUnavailable, match="no liblouis text table"):
        LiblouisText(linearise, "de", native=FakeLiblouis())  # type: ignore[arg-type]


def test_the_document_is_linearised_before_translation() -> None:
    native = FakeLiblouis()
    LiblouisText(linearise, "es", native=native).unicode(  # type: ignore[arg-type]
        [Character("a"), Character("1")]
    )
    assert native.calls[-1] == ("es-g1.ctb", "a1")


# --- the braille ladder -----------------------------------------------------


def test_liblouis_is_used_for_braille_when_mathcat_is_absent(catalog: Catalog) -> None:
    outputs = create_outputs(
        catalog,
        "es",
        directory=DATA,
        prefer_mathcat=False,
        liblouis_native=FakeLiblouis(),  # type: ignore[arg-type]
    )
    assert outputs.speech_backend == "tables"  # no MathCAT -> our labels
    assert outputs.braille_backend == "liblouis"
    assert outputs.braille is not None
    assert outputs.braille.ascii(expression()) == "#a6#b"


def test_tables_are_the_last_resort(catalog: Catalog) -> None:
    outputs = create_outputs(
        catalog, "es", directory=DATA, prefer_mathcat=False, prefer_liblouis=False
    )
    assert outputs.braille_backend == "tables"
    assert outputs.braille is not None


def test_real_liblouis_binding_is_optional() -> None:
    """When the native library is absent, is_available() is simply False."""
    from disvimat.core.liblouis import find_library_path, is_available

    # Either it is installed (then available) or not (then not) — never raises.
    assert is_available() in (True, False)
    assert find_library_path() is None or find_library_path().is_file()


def test_native_binding_signature_matches_liblouis() -> None:
    """The wrapper exposes the methods the ladder relies on."""
    assert hasattr(Liblouis, "translate")
    assert hasattr(Liblouis, "version")
