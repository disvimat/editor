"""Perfiles de usuario A7: los niveles limitan los elementos disponibles."""

from pathlib import Path

import pytest

from disvimat.core.editor import crear_editor

DATOS = Path(__file__).resolve().parents[1] / "data"


def test_perfil_inicial_bloquea_los_niveles_altos() -> None:
    editor = crear_editor(DATOS, perfil="inicial")
    assert editor.pulsar("Ctrl+Shift+R") is None  # raíz de índice: nivel 3
    assert editor.pulsar("Ctrl+R") is None  # raíz cuadrada: nivel 2
    resultado = editor.pulsar("Ctrl+F")  # fracción: nivel 1
    assert resultado is not None


def test_los_comandos_no_dependen_del_nivel() -> None:
    editor = crear_editor(DATOS, perfil="inicial")
    editor.escribir("1")
    resultado = editor.pulsar("Left")
    assert resultado is not None
    assert resultado.verbalizacion == "1"


def test_perfil_avanzado_lo_permite_todo() -> None:
    editor = crear_editor(DATOS, perfil="avanzado")
    assert editor.pulsar("Ctrl+Shift+R") is not None


def test_perfil_desconocido_da_error_claro() -> None:
    with pytest.raises(ValueError, match="perfil desconocido"):
        crear_editor(DATOS, perfil="inexistente")
