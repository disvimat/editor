"""Internacionalización: gettext con reserva y tablas por lengua (E6)."""

from pathlib import Path

from disvimat.core.editor import crear_editor
from disvimat.core.i18n import _, instalar
from disvimat.core.tablas import ruta_tabla_lengua

DATOS = Path(__file__).resolve().parents[1] / "data"


def test_gettext_recurre_a_la_cadena_fuente() -> None:
    instalar("xx")  # lengua sin catálogo compilado
    assert _("&Salir") == "&Salir"


def test_tabla_por_lengua_con_reserva_al_espanol() -> None:
    assert ruta_tabla_lengua(DATOS, "etiquetas", "es").name == "etiquetas.es.json"
    assert ruta_tabla_lengua(DATOS, "etiquetas", "fr").name == "etiquetas.es.json"


def test_editor_en_lengua_sin_tablas_recurre_al_espanol() -> None:
    editor = crear_editor(DATOS, lengua="fr")
    resultado = editor.pulsar("+")
    assert resultado is not None
    assert resultado.verbalizacion == "más"
