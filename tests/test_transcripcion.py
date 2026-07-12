"""Transcripción braille de 6 puntos dirigida por tablas (B5/C3)."""

from pathlib import Path

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.transcripcion.braille import Transcriptor, crear_transcriptor

DATOS = Path(__file__).resolve().parents[1] / "data"


def transcriptor() -> Transcriptor:
    return crear_transcriptor(DATOS, lengua="es")


def test_numero_lleva_prefijo_una_vez_por_grupo() -> None:
    nodos: list[Nodo] = [Caracter("1"), Caracter("2")]
    assert transcriptor().unicode(nodos) == "⠼⠁⠃"


def test_el_espacio_reinicia_el_grupo_numerico() -> None:
    nodos: list[Nodo] = [Caracter("1"), Caracter(" "), Caracter("2")]
    assert transcriptor().unicode(nodos) == "⠼⠁⠀⠼⠃"


def test_letras_sin_prefijo_y_mayuscula_con_prefijo() -> None:
    assert transcriptor().unicode([Caracter("a"), Caracter("b")]) == "⠁⠃"
    assert transcriptor().unicode([Caracter("A")]) == "⠨⠁"


def test_signos_desde_la_tabla() -> None:
    nodos: list[Nodo] = [Caracter("1"), Signo("mas"), Caracter("2")]
    assert transcriptor().unicode(nodos) == "⠼⠁⠖⠼⠃"


def test_fraccion_con_partes_y_prefijos_por_hueco() -> None:
    nodos: list[Nodo] = [Estructura("fraccion", [[Caracter("1")], [Caracter("2")]])]
    assert transcriptor().unicode(nodos) == "⠼⠁⠌⠼⠃"


def test_hueco_vacio_y_caracter_desconocido_usan_relleno() -> None:
    assert transcriptor().unicode([Estructura("raiz", [[]])]) == "⠩⠿⠴"
    assert transcriptor().unicode([Caracter("@")]) == "⠿"


def test_exportacion_ascii_bra() -> None:
    nodos: list[Nodo] = [Caracter("1"), Signo("mas"), Caracter("2")]
    assert transcriptor().ascii(nodos) == "#a6#b"
