"""Render lineal con glifos, plantillas y posición del cursor."""

from pathlib import Path

from disvimat.core.documento import Caracter, Documento, Estructura, Signo
from disvimat.core.presentacion import Presentador
from disvimat.core.tablas import EntradaGlifo, Tabla, cargar_tabla

DATOS = Path(__file__).resolve().parents[1] / "data"


def presentador() -> Presentador:
    return Presentador(cargar_tabla(DATOS / "glifos.json", EntradaGlifo))


def test_documento_vacio() -> None:
    assert presentador().render(Documento()) == ("", 0)


def test_render_lineal_con_plantilla() -> None:
    documento = Documento()
    documento.raiz = [
        Caracter("1"),
        Signo("mas"),
        Estructura("fraccion", [[Caracter("2")], [Caracter("3")]]),
    ]
    texto, posicion = presentador().render(documento)
    assert texto == "1+(2∕3)"
    assert posicion == 0  # cursor al inicio


def test_hueco_vacio_se_presenta_con_glifo() -> None:
    documento = Documento()
    documento.raiz = [Estructura("fraccion", [[Caracter("2")], []])]
    texto, _ = presentador().render(documento)
    assert texto == "(2∕□)"


def test_cursor_dentro_de_hueco_vacio() -> None:
    documento = Documento()
    documento.insertar(Caracter("1"))
    documento.insertar(Signo("mas"))
    documento.insertar(Estructura("fraccion", [[], []]))
    texto, posicion = presentador().render(documento)
    assert texto == "1+(□∕□)"
    assert posicion == texto.index("□")


def test_estructura_sin_plantilla_usa_forma_generica() -> None:
    tabla = Tabla[EntradaGlifo](
        tabla="glifos",
        version=1,
        entradas=[EntradaGlifo(id="hueco", glifo="□"), EntradaGlifo(id="caja", glifo="◧")],
    )
    documento = Documento()
    documento.raiz = [Estructura("caja", [[Caracter("1")], []])]
    texto, _ = Presentador(tabla).render(documento)
    assert texto == "◧(1;□)"
