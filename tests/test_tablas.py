"""Validación de la envoltura común y de los modelos de tabla."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from disvimat.core.elementos import Elemento, Registro, TipoElemento
from disvimat.core.tablas import (
    Catalogo,
    EntradaEtiqueta,
    EntradaGlifo,
    EntradaTecla,
    Tabla,
    cargar_tabla,
    dir_datos,
)

DATOS = Path(__file__).resolve().parents[1] / "data"


def test_dir_datos_apunta_al_proyecto() -> None:
    assert dir_datos() == DATOS


def test_carga_catalogo() -> None:
    catalogo = Catalogo.cargar(DATOS / "elementos.json")
    assert len(catalogo) > 0
    assert "fraccion" in catalogo
    assert catalogo["fraccion"].tipo is TipoElemento.ESTRUCTURA
    assert catalogo["fraccion"].aridad == 2


@pytest.mark.parametrize(
    ("archivo", "tipo_entrada"),
    [
        ("teclas_signos.json", EntradaTecla),
        ("teclas_comandos.json", EntradaTecla),
        ("glifos.json", EntradaGlifo),
        ("etiquetas.es.json", EntradaEtiqueta),
    ],
)
def test_carga_tablas(archivo: str, tipo_entrada: type[Registro]) -> None:
    tabla = cargar_tabla(DATOS / archivo, tipo_entrada)
    assert tabla.entradas


def test_ids_duplicados_rechazados() -> None:
    with pytest.raises(ValidationError, match="duplicado"):
        Tabla[EntradaGlifo](
            tabla="glifos",
            version=1,
            entradas=[EntradaGlifo(id="mas", glifo="+"), EntradaGlifo(id="mas", glifo="-")],
        )


def test_estructura_sin_aridad_rechazada() -> None:
    with pytest.raises(ValidationError, match="aridad"):
        Elemento(id="x", tipo=TipoElemento.ESTRUCTURA, categoria="algebra")


def test_signo_con_aridad_rechazado() -> None:
    with pytest.raises(ValidationError, match="aridad"):
        Elemento(id="x", tipo=TipoElemento.SIGNO, categoria="aritmetica", aridad=2)


def test_partes_desconocidas_rechazadas() -> None:
    with pytest.raises(ValidationError, match="partes desconocidas"):
        EntradaEtiqueta(id="x", etiqueta="x", partes={"medio": "y"})
