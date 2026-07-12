"""El núcleo no importa nada de interfaz (principio 1 del plan)."""

import subprocess
import sys

_CODIGO = (
    "import sys; "
    "import disvimat.core.integridad, disvimat.core.tablas, disvimat.core.elementos; "
    "import disvimat.core.documento, disvimat.core.editor, disvimat.core.teclado; "
    "import disvimat.core.presentacion, disvimat.core.verbalizacion; "
    "import disvimat.core.filtros.mathml, disvimat.export.xhtml; "
    "prohibidos = sorted({m.split('.')[0] for m in sys.modules} "
    "& {'wx', 'fastapi', 'flask', 'PySide6', 'PyQt6', 'tkinter'}); "
    "print(prohibidos); "
    "sys.exit(1 if prohibidos else 0)"
)


def test_core_sin_dependencias_de_interfaz() -> None:
    resultado = subprocess.run(
        [sys.executable, "-c", _CODIGO], check=False, capture_output=True, text=True
    )
    assert resultado.returncode == 0, f"el núcleo importó módulos de UI: {resultado.stdout}"
