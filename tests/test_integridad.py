"""Coherencia entre las tablas de data/ (principio 5 del plan).

Si uno de estos tests falla, hay que corregir las tablas, no los tests:
son el contrato que impide que una tabla incoherente llegue al usuario.
"""

from pathlib import Path

import pytest

from disvimat.core.elementos import TipoElemento
from disvimat.core.integridad import conflictos_de_teclas, ids_desconocidos, ids_sin_cubrir
from disvimat.core.tablas import (
    Catalogo,
    EntradaBraille,
    EntradaEtiqueta,
    EntradaGlifo,
    EntradaTecla,
    Tabla,
    cargar_tabla,
)

DATOS = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def catalogo() -> Catalogo:
    return Catalogo.cargar(DATOS / "elementos.json")


@pytest.fixture(scope="module")
def teclas_signos() -> Tabla[EntradaTecla]:
    return cargar_tabla(DATOS / "teclas_signos.json", EntradaTecla)


@pytest.fixture(scope="module")
def teclas_comandos() -> Tabla[EntradaTecla]:
    return cargar_tabla(DATOS / "teclas_comandos.json", EntradaTecla)


def test_referencias_de_todas_las_tablas(catalogo: Catalogo) -> None:
    tablas = [
        ("teclas_signos.json", EntradaTecla),
        ("teclas_comandos.json", EntradaTecla),
        ("teclas_numpad.json", EntradaTecla),
        ("glifos.json", EntradaGlifo),
        ("etiquetas.es.json", EntradaEtiqueta),
        ("br6.es.json", EntradaBraille),
    ]
    for archivo, tipo_entrada in tablas:
        tabla = cargar_tabla(DATOS / archivo, tipo_entrada)
        assert ids_desconocidos(tabla, catalogo) == set(), archivo


def test_glifos_cubren_signos_y_estructuras(catalogo: Catalogo) -> None:
    tabla = cargar_tabla(DATOS / "glifos.json", EntradaGlifo)
    tipos = {TipoElemento.SIGNO, TipoElemento.ESTRUCTURA}
    assert ids_sin_cubrir(tabla, catalogo, tipos) == set()


def test_etiquetas_cubren_todos_los_elementos(catalogo: Catalogo) -> None:
    tabla = cargar_tabla(DATOS / "etiquetas.es.json", EntradaEtiqueta)
    tipos = set(TipoElemento)
    assert ids_sin_cubrir(tabla, catalogo, tipos) == set()


def test_teclas_signos_no_referencia_comandos(
    catalogo: Catalogo, teclas_signos: Tabla[EntradaTecla]
) -> None:
    for entrada in teclas_signos.entradas:
        assert catalogo[entrada.id].tipo is not TipoElemento.COMANDO, entrada.id


def test_teclas_comandos_solo_referencia_comandos(
    catalogo: Catalogo, teclas_comandos: Tabla[EntradaTecla]
) -> None:
    for entrada in teclas_comandos.entradas:
        assert catalogo[entrada.id].tipo is TipoElemento.COMANDO, entrada.id


def test_br6_cubre_signos_y_estructuras(catalogo: Catalogo) -> None:
    tabla = cargar_tabla(DATOS / "br6.es.json", EntradaBraille)
    tipos = {TipoElemento.SIGNO, TipoElemento.ESTRUCTURA}
    assert ids_sin_cubrir(tabla, catalogo, tipos) == set()


def test_sin_conflictos_de_pulsaciones(
    teclas_signos: Tabla[EntradaTecla], teclas_comandos: Tabla[EntradaTecla]
) -> None:
    teclas_numpad = cargar_tabla(DATOS / "teclas_numpad.json", EntradaTecla)
    assert conflictos_de_teclas(teclas_signos, teclas_comandos, teclas_numpad) == {}
