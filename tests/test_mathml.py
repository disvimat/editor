"""Filtro A1 y exportación C1: ida y vuelta MathML ↔ árbol DisvimatEditor."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.filtros.mathml import ErrorDeFiltro, FiltroMathML
from disvimat.core.tablas import Catalogo
from disvimat.export.xhtml import ExportadorXHTML

DATOS = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
def catalogo() -> Catalogo:
    return Catalogo.cargar(DATOS / "elementos.json")


def test_ida_y_vuelta(catalogo: Catalogo) -> None:
    nodos: list[Nodo] = [
        Caracter("1"),
        Caracter("2"),
        Signo("mas"),
        Estructura(
            "fraccion",
            [[Caracter("3")], [Caracter("4"), Signo("menos"), Caracter("5")]],
        ),
    ]
    texto = ET.tostring(ExportadorXHTML(catalogo).mathml(nodos), encoding="unicode")
    assert FiltroMathML(catalogo).desde_texto(texto) == nodos


def test_ida_y_vuelta_de_raiz_y_potencia(catalogo: Catalogo) -> None:
    nodos: list[Nodo] = [
        Estructura("raiz", [[Caracter("x")]]),
        Signo("mas"),
        Estructura("potencia", [[Caracter("x")], [Caracter("2")]]),
    ]
    texto = ET.tostring(ExportadorXHTML(catalogo).mathml(nodos), encoding="unicode")
    assert FiltroMathML(catalogo).desde_texto(texto) == nodos


def test_huecos_vacios_sobreviven(catalogo: Catalogo) -> None:
    nodos: list[Nodo] = [Estructura("fraccion", [[], []])]
    texto = ET.tostring(ExportadorXHTML(catalogo).mathml(nodos), encoding="unicode")
    assert FiltroMathML(catalogo).desde_texto(texto) == nodos


def test_digitos_agrupados_en_mn(catalogo: Catalogo) -> None:
    nodos: list[Nodo] = [Caracter("1"), Caracter("2"), Caracter("3")]
    math = ExportadorXHTML(catalogo).mathml(nodos)
    assert [(hijo.tag, hijo.text) for hijo in math] == [("mn", "123")]


def test_importa_mathml_con_espacio_de_nombres(catalogo: Catalogo) -> None:
    texto = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>7</mn><mo>+</mo><mn>1</mn></math>'
    nodos = FiltroMathML(catalogo).desde_texto(texto)
    assert nodos == [Caracter("7"), Signo("mas"), Caracter("1")]


def test_signo_desconocido_da_error_claro(catalogo: Catalogo) -> None:
    with pytest.raises(ErrorDeFiltro, match="sin correspondencia"):
        FiltroMathML(catalogo).desde_texto("<math><mo>∮</mo></math>")


def test_documento_xhtml_completo(catalogo: Catalogo) -> None:
    documento = ExportadorXHTML(catalogo).documento_xhtml([Caracter("1")], titulo="Prueba")
    assert "<title>Prueba</title>" in documento
    assert "<math" in documento and "<mn>1</mn>" in documento
