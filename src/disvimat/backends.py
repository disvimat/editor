"""Choosing where speech and braille come from.

The policy lives here, in one place, and follows what NVDA does: each
engine handles what it is best at, with graceful fallback.

- **Speech:** MathCAT reads mathematical notation, our label tables narrate
  the editing. MathCAT leads when installed and covers the language.
- **Braille:** MathCAT provides normative *math* braille (CMU, UEB…);
  liblouis provides official *text* braille (letters, digits, words) with
  its maintained tables; our own hand tables are the last resort. So the
  ladder is **MathCAT → liblouis → tables**.

When an engine is missing the next one takes over, so the editor always
works. This module lives outside ``core`` on purpose: it is the only place
that combines the core with the MathML exporter and the presenter.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.liblouis import Liblouis, LiblouisText, LiblouisUnavailable
from disvimat.core.mathcat import MathCATBackend, MathCATUnavailable, _Library
from disvimat.core.output import BrailleProvider, ExpressionReader
from disvimat.core.presentation import Presenter
from disvimat.core.tables import Catalog, GlyphEntry, Table, data_dir, load_table
from disvimat.core.transcription.braille import BrailleTablesMissing, create_transcriber
from disvimat.export.xhtml import XHTMLExporter

#: Force speech and braille onto our own tables even when the external
#: engines are installed. The test suite sets these so results do not depend
#: on whether MathCAT / liblouis happen to be present (CI has neither).
DISABLE_MATHCAT_ENV = "DISVIMAT_NO_MATHCAT"
DISABLE_LIBLOUIS_ENV = "DISVIMAT_NO_LIBLOUIS"


@dataclass(frozen=True)
class Outputs:
    """The speech and braille engines chosen for a session.

    ``reader`` is ``None`` when the editor should use its own label
    tables; ``braille`` is ``None`` when braille is unavailable and the
    interfaces must disable their braille features.
    """

    reader: ExpressionReader | None
    braille: BrailleProvider | None
    speech_backend: str
    braille_backend: str


def create_outputs(
    catalog: Catalog,
    language: str,
    *,
    directory: Path | None = None,
    prefer_mathcat: bool = True,
    prefer_liblouis: bool = True,
    library: _Library | None = None,
    rules_dir: Path | None = None,
    liblouis_native: Liblouis | None = None,
) -> Outputs:
    """Pick the speech and braille engines for a language.

    Injected engines (``library``, ``liblouis_native``) always go through,
    which is how the tests drive the adapters; auto-detection is what the
    ``DISVIMAT_NO_*`` switches turn off.
    """
    directory = directory or data_dir()
    mathml_of = XHTMLExporter(catalog).mathml_text
    reader: ExpressionReader | None = None
    braille: BrailleProvider | None = None
    speech_backend = "tables"
    braille_backend = "none"

    # --- speech and math braille: MathCAT ------------------------------------
    mathcat_off = library is None and bool(os.environ.get(DISABLE_MATHCAT_ENV))
    if prefer_mathcat and not mathcat_off:
        try:
            backend = MathCATBackend(mathml_of, language, library=library, rules_dir=rules_dir)
        except MathCATUnavailable:
            pass  # not installed, or a language MathCAT does not cover
        else:
            reader, speech_backend = backend, "mathcat"
            if backend.supports_braille:
                braille, braille_backend = backend, "mathcat"

    # --- text braille: liblouis (below MathCAT, above our tables) ------------
    liblouis_off = liblouis_native is None and bool(os.environ.get(DISABLE_LIBLOUIS_ENV))
    if braille is None and prefer_liblouis and not liblouis_off:
        try:
            glyphs: Table[GlyphEntry] = load_table(directory / "glyphs.json", GlyphEntry)
            linearise = Presenter(glyphs).text
            braille = LiblouisText(linearise, language, native=liblouis_native)
        except (LiblouisUnavailable, OSError):
            braille = None
        else:
            braille_backend = "liblouis"

    # --- last resort: our own braille tables ---------------------------------
    if braille is None:
        try:
            braille = create_transcriber(directory, language=language)
        except BrailleTablesMissing:
            braille = None
        else:
            braille_backend = "tables"

    return Outputs(
        reader=reader,
        braille=braille,
        speech_backend=speech_backend,
        braille_backend=braille_backend,
    )
