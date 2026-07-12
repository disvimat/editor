"""Operaciones del árbol del documento: edición, navegación y deshacer."""

from disvimat.core.documento import Caracter, Documento, Estructura, Signo


def fraccion() -> Estructura:
    return Estructura("fraccion", [[], []])


def test_insertar_caracteres_y_signos() -> None:
    documento = Documento()
    documento.insertar(Caracter("1"))
    documento.insertar(Signo("mas"))
    assert len(documento.raiz) == 2
    assert documento.indice_cursor() == 2


def test_insertar_estructura_entra_al_primer_hueco() -> None:
    documento = Documento()
    documento.insertar(fraccion())
    assert documento.camino_cursor() == [(0, 0)]
    assert documento.indice_cursor() == 0
    documento.insertar(Caracter("2"))
    estructura = documento.raiz[0]
    assert isinstance(estructura, Estructura)
    assert estructura.huecos[0] == [Caracter("2")]


def test_salir_deja_el_cursor_tras_la_estructura() -> None:
    documento = Documento()
    documento.insertar(Caracter("1"))
    documento.insertar(fraccion())
    salida = documento.salir()
    assert isinstance(salida, Estructura)
    assert documento.camino_cursor() == []
    assert documento.indice_cursor() == 2


def test_entrar_e_izquierda_y_derecha() -> None:
    documento = Documento()
    documento.insertar(fraccion())
    documento.insertar(Caracter("2"))
    documento.salir()
    cruzado = documento.izquierda()
    assert isinstance(cruzado, Estructura)
    estructura = documento.entrar()
    assert isinstance(estructura, Estructura)
    assert documento.derecha() == Caracter("2")
    assert documento.derecha() is None  # fin del hueco


def test_hueco_siguiente_y_salida_desde_el_ultimo() -> None:
    documento = Documento()
    documento.insertar(fraccion())
    assert documento.hueco_siguiente() == 1
    assert documento.camino_cursor() == [(0, 1)]
    assert documento.hueco_siguiente() is None  # último hueco: sale
    assert documento.camino_cursor() == []
    assert documento.indice_cursor() == 1


def test_borrar_atras_borra_estructuras_enteras() -> None:
    documento = Documento()
    documento.insertar(fraccion())
    documento.salir()
    borrado = documento.borrar_atras()
    assert isinstance(borrado, Estructura)
    assert documento.vacio()


def test_deshacer_restaura_arbol_y_cursor() -> None:
    documento = Documento()
    documento.insertar(Caracter("1"))
    documento.insertar(fraccion())
    documento.insertar(Caracter("2"))
    documento.salir()
    documento.borrar_atras()
    assert len(documento.raiz) == 1
    assert documento.deshacer()
    assert len(documento.raiz) == 2
    assert documento.indice_cursor() == 2  # como antes de borrar
    assert documento.rehacer()
    assert len(documento.raiz) == 1


def test_deshacer_sin_historia() -> None:
    documento = Documento()
    assert not documento.deshacer()
    assert not documento.rehacer()
