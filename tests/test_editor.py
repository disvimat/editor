"""Integración del editor: teclear como lo haría la interfaz."""

from pathlib import Path

import pytest

from disvimat.core.editor import Editor, crear_editor

DATOS = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def editor() -> Editor:
    return crear_editor(DATOS)


def test_escribir_y_signos(editor: Editor) -> None:
    editor.escribir("1")
    resultado = editor.pulsar("+")
    assert resultado is not None
    assert resultado.texto == "1+"
    assert resultado.posicion == 2
    assert resultado.verbalizacion == "más"


def test_edicion_de_una_fraccion(editor: Editor) -> None:
    editor.escribir("1")
    editor.pulsar("+")
    resultado = editor.pulsar("Ctrl+F")
    assert resultado is not None
    assert resultado.texto == "1+(□∕□)"
    assert resultado.posicion == resultado.texto.index("□")
    assert resultado.verbalizacion == "fracción, hueco 1"

    editor.escribir("2")
    resultado = editor.pulsar("Tab")
    assert resultado is not None
    assert resultado.texto == "1+(2∕□)"
    assert resultado.verbalizacion == "hueco 2"

    editor.escribir("3")
    resultado = editor.pulsar("Tab")  # último hueco: sale de la estructura
    assert resultado is not None
    assert resultado.texto == "1+(2∕3)"
    assert resultado.posicion == len(resultado.texto)
    assert resultado.verbalizacion == "salir de la estructura: fracción"


def test_leer_linea(editor: Editor) -> None:
    for tecla in ["1", "+"]:
        editor.escribir(tecla) if tecla.isdigit() else editor.pulsar(tecla)
    editor.pulsar("Ctrl+F")
    editor.escribir("2")
    editor.pulsar("Tab")
    editor.escribir("3")
    resultado = editor.pulsar("Ctrl+Shift+L")
    assert resultado is not None
    assert resultado.verbalizacion == "1 más fracción 2 entre 3 fin de fracción"


def test_navegacion_verbaliza_lo_cruzado(editor: Editor) -> None:
    editor.escribir("1")
    editor.pulsar("+")
    resultado = editor.pulsar("Left")
    assert resultado is not None
    assert resultado.verbalizacion == "más"
    resultado = editor.pulsar("Left")
    assert resultado is not None
    assert resultado.verbalizacion == "1"
    resultado = editor.pulsar("Left")
    assert resultado is not None
    assert resultado.verbalizacion == "inicio de línea"


def test_borrar_verbaliza_lo_borrado(editor: Editor) -> None:
    editor.escribir("1")
    editor.pulsar("+")
    resultado = editor.pulsar("Backspace")
    assert resultado is not None
    assert resultado.texto == "1"
    assert resultado.verbalizacion == "borrar hacia atrás: más"


def test_deshacer_y_rehacer(editor: Editor) -> None:
    editor.escribir("1")
    editor.escribir("2")
    resultado = editor.pulsar("Ctrl+Z")
    assert resultado is not None
    assert resultado.texto == "1"
    resultado = editor.pulsar("Ctrl+Y")
    assert resultado is not None
    assert resultado.texto == "12"


def test_pulsacion_no_asignada(editor: Editor) -> None:
    assert editor.pulsar("F9") is None
    assert editor.pulsar("Ctrl+Alt+Q") is None


def test_bloque_numerico(editor: Editor) -> None:
    editor.escribir("1")
    resultado = editor.pulsar("NumAdd")
    assert resultado is not None
    assert resultado.texto == "1+"
    assert resultado.verbalizacion == "más"


def test_importar_lo_exportado(editor: Editor) -> None:
    from disvimat.core.filtros.mathml import FiltroMathML
    from disvimat.export.xhtml import ExportadorXHTML

    editor.escribir("1")
    editor.pulsar("+")
    editor.pulsar("Ctrl+F")
    editor.escribir("2")
    editor.pulsar("Tab")
    editor.escribir("3")
    documento = ExportadorXHTML(editor.catalogo).documento_xhtml(editor.documento.raiz)

    receptor = crear_editor(DATOS)
    resultado = receptor.cargar(FiltroMathML(receptor.catalogo).desde_xhtml(documento))
    assert resultado.texto == "1+(2∕3)"
    assert resultado.posicion == len(resultado.texto)
    assert resultado.verbalizacion == "1 más fracción 2 entre 3 fin de fracción"

    # la importación es deshacible
    deshecho = receptor.pulsar("Ctrl+Z")
    assert deshecho is not None
    assert deshecho.texto == ""
