"""The core imports nothing from the interface layers (principle 1)."""

import subprocess
import sys

_CODE = (
    "import sys; "
    "import disvimat.core.integrity, disvimat.core.tables, disvimat.core.elements; "
    "import disvimat.core.document, disvimat.core.editor, disvimat.core.keyboard; "
    "import disvimat.core.presentation, disvimat.core.speech, disvimat.core.calculator; "
    "import disvimat.core.filters.mathml, disvimat.export.xhtml; "
    "import disvimat.core.transcription.braille, disvimat.core.ui_text, disvimat.core.dvm; "
    "forbidden = sorted({m.split('.')[0] for m in sys.modules} "
    "& {'wx', 'fastapi', 'flask', 'PySide6', 'PyQt6', 'tkinter'}); "
    "print(forbidden); "
    "sys.exit(1 if forbidden else 0)"
)


def test_core_has_no_interface_dependencies() -> None:
    outcome = subprocess.run(
        [sys.executable, "-c", _CODE], check=False, capture_output=True, text=True
    )
    assert outcome.returncode == 0, f"the core imported UI modules: {outcome.stdout}"
