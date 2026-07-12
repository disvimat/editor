"""Lectura del documento con las etiquetas B2."""

from pathlib import Path

from disvimat.core.documento import Caracter, Estructura, Signo
from disvimat.core.tablas import EntradaEtiqueta, cargar_tabla
from disvimat.core.verbalizacion import Verbalizador

DATOS = Path(__file__).resolve().parents[1] / "data"


def verbalizador() -> Verbalizador:
    return Verbalizador(cargar_tabla(DATOS / "etiquetas.es.json", EntradaEtiqueta))


def test_signo() -> None:
    assert verbalizador().nodo(Signo("mas")) == "más"


def test_caracteres_contiguos_se_agrupan() -> None:
    nodos = [Caracter("1"), Caracter("2"), Signo("mas"), Caracter("3")]
    assert verbalizador().secuencia(nodos) == "12 más 3"


def test_fraccion_con_partes() -> None:
    estructura = Estructura("fraccion", [[Caracter("2")], [Caracter("3")]])
    assert verbalizador().nodo(estructura) == "fracción 2 entre 3 fin de fracción"


def test_potencia_lee_primero_la_base() -> None:
    estructura = Estructura("potencia", [[Caracter("x")], [Caracter("2")]])
    assert verbalizador().nodo(estructura) == "x elevado a 2 fin de exponente"


def test_hueco_vacio_se_verbaliza() -> None:
    estructura = Estructura("fraccion", [[Caracter("2")], []])
    assert verbalizador().nodo(estructura) == "fracción 2 entre hueco fin de fracción"


def test_secuencia_vacia_es_hueco() -> None:
    assert verbalizador().secuencia([]) == "hueco"
