"""Localización de la interfaz con gettext (módulo E6).

Las cadenas del código fuente están en español (lengua de referencia);
las traducciones se cargan de ``src/disvimat/locale/<lengua>/LC_MESSAGES/
disvimat.mo``. Si no hay catálogo para la lengua pedida, se usan las
cadenas originales sin fallar.

Las verbalizaciones y presentaciones del editor NO pasan por aquí: se
localizan con sus propias tablas por lengua (``etiquetas.<lengua>.json``,
``br6.<lengua>.json``...), resueltas con
:func:`disvimat.core.tablas.ruta_tabla_lengua`.
"""

import gettext
from pathlib import Path

_DIR_LOCALE = Path(__file__).resolve().parents[1] / "locale"

_traduccion: gettext.NullTranslations = gettext.NullTranslations()


def instalar(lengua: str) -> None:
    """Activa la lengua de la interfaz (con reserva a las cadenas fuente)."""
    global _traduccion
    _traduccion = gettext.translation(
        "disvimat", localedir=_DIR_LOCALE, languages=[lengua], fallback=True
    )


def _(mensaje: str) -> str:
    """Traduce una cadena de la interfaz a la lengua activa."""
    return _traduccion.gettext(mensaje)
