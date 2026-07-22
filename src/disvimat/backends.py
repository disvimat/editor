"""Choosing where speech and braille come from.

Policy in one place: **MathCAT leads, our tables are the fallback.**
MathCAT implements the normative mathematical braille codes (CMU for
Spanish) and reads notation better than our tables can, so it is used
whenever it is installed and covers the language. When it is missing —
which is the common case today, since it is not on PyPI — everything
degrades to the table-driven engines and the editor keeps working.

This module lives outside ``core`` on purpose: it is the only place that
combines the core with the MathML exporter, keeping the core itself free
of that dependency.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.mathcat import MathCATBackend, MathCATUnavailable, _Library
from disvimat.core.output import BrailleProvider, ExpressionReader
from disvimat.core.tables import Catalog
from disvimat.core.transcription.braille import BrailleTablesMissing, create_transcriber
from disvimat.export.xhtml import XHTMLExporter

#: Set this environment variable to keep speech and braille on our own
#: tables even when MathCAT is installed. The test suite sets it so results
#: do not depend on whether MathCAT happens to be present (CI has none).
DISABLE_ENV = "DISVIMAT_NO_MATHCAT"


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
    library: _Library | None = None,
    rules_dir: Path | None = None,
) -> Outputs:
    """Pick the engines for a language, preferring MathCAT over the tables."""
    mathml_of = XHTMLExporter(catalog).mathml_text
    reader: ExpressionReader | None = None
    braille: BrailleProvider | None = None
    speech_backend = "tables"
    braille_backend = "none"

    # The disable switch only affects auto-detection; an injected library
    # (the tests) always goes through, so the adapter stays testable.
    disabled = library is None and bool(os.environ.get(DISABLE_ENV))
    if prefer_mathcat and not disabled:
        try:
            backend = MathCATBackend(mathml_of, language, library=library, rules_dir=rules_dir)
        except MathCATUnavailable:
            pass  # not installed, or a language MathCAT does not cover
        else:
            reader, speech_backend = backend, "mathcat"
            if backend.supports_braille:
                braille, braille_backend = backend, "mathcat"

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
