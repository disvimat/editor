"""Calculadora A8: evaluación exacta y errores localizables; bloqueo A9."""

from pathlib import Path

import pytest

from disvimat.core.calculadora import (
    MSG_DIVISION_CERO,
    MSG_NO_CALCULABLE,
    Calculadora,
    ErrorDeCalculo,
)
from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.editor import crear_editor

DATOS = Path(__file__).resolve().parents[1] / "data"


def num(texto: str) -> list[Nodo]:
    return [Caracter(c) for c in texto]


def test_precedencia_de_operadores() -> None:
    # 2 + 3 * 4 = 14
    nodos = [*num("2"), Signo("mas"), *num("3"), Signo("por"), *num("4")]
    assert Calculadora().evaluar(nodos) == "14"


def test_fraccion_exacta() -> None:
    # 1/2 + 1/2 = 1
    mitad = Estructura("fraccion", [num("1"), num("2")])
    nodos: list[Nodo] = [mitad, Signo("mas"), Estructura("fraccion", [num("1"), num("2")])]
    assert Calculadora().evaluar(nodos) == "1"


def test_decimal_con_coma() -> None:
    # 1,5 * 2 = 3
    nodos = [*num("1"), Signo("coma_decimal"), *num("5"), Signo("por"), *num("2")]
    assert Calculadora().evaluar(nodos) == "3"


def test_potencia_y_raiz_exactas() -> None:
    assert Calculadora().evaluar([Estructura("potencia", [num("2"), num("10")])]) == "1024"
    assert Calculadora().evaluar([Estructura("raiz", [num("9")])]) == "3"


def test_negativo_unario() -> None:
    # -3 + 5 = 2
    nodos = [Signo("menos"), *num("3"), Signo("mas"), *num("5")]
    assert Calculadora().evaluar(nodos) == "2"


def test_division_entre_cero() -> None:
    nodos = [*num("1"), Signo("entre"), *num("0")]
    with pytest.raises(ErrorDeCalculo) as excinfo:
        Calculadora().evaluar(nodos)
    assert excinfo.value.id_mensaje == MSG_DIVISION_CERO


def test_expresion_incompleta_no_calculable() -> None:
    nodos = [*num("1"), Signo("mas")]
    with pytest.raises(ErrorDeCalculo) as excinfo:
        Calculadora().evaluar(nodos)
    assert excinfo.value.id_mensaje == MSG_NO_CALCULABLE


def test_comando_calcular_en_el_editor() -> None:
    editor = crear_editor(DATOS)
    for pulsacion in ["2", "+", "3", "*", "4"]:
        editor.escribir(pulsacion) if pulsacion.isdigit() else editor.pulsar(pulsacion)
    resultado = editor.pulsar("Ctrl+Return")
    assert resultado is not None
    assert resultado.verbalizacion == "resultado: 14"


def test_error_de_calculo_se_verbaliza_localizado() -> None:
    editor = crear_editor(DATOS)
    for pulsacion in ["1", "/", "0"]:
        editor.escribir(pulsacion) if pulsacion.isdigit() else editor.pulsar(pulsacion)
    resultado = editor.pulsar("Ctrl+Return")
    assert resultado is not None
    assert resultado.verbalizacion == "división entre cero"


def test_bloqueo_del_profesor() -> None:
    editor = crear_editor(DATOS, perfil="examen")
    editor.escribir("2")
    resultado = editor.pulsar("Ctrl+Return")
    assert resultado is not None
    assert resultado.verbalizacion == "calculadora bloqueada"
