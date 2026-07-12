"""Árbol del documento DisvimatEditor: nodos, cursor, edición y deshacer.

El documento es una secuencia de nodos; una estructura contiene huecos,
que son a su vez secuencias de nodos. El cursor se representa como un
camino de descenso por estructuras más un índice dentro de la secuencia
actual: el cursor está siempre *entre* dos nodos (o en un extremo).

Este módulo no verbaliza ni presenta nada: devuelve los nodos afectados
por cada operación y las capas de presentación deciden qué mostrar o
anunciar (principio 1 del plan).
"""

import copy
from dataclasses import dataclass, field


@dataclass
class Caracter:
    """Un carácter de texto plano (dígitos, letras, espacios)."""

    texto: str


@dataclass
class Signo:
    """Un signo del catálogo (sin huecos)."""

    id_elemento: str


@dataclass
class Estructura:
    """Una estructura del catálogo con sus huecos (uno por aridad)."""

    id_elemento: str
    huecos: list[list["Nodo"]]


Nodo = Caracter | Signo | Estructura


@dataclass
class _Cursor:
    """Posición de edición: descenso por estructuras + índice en la secuencia.

    Cada paso del camino es ``(índice del nodo estructura, índice del hueco)``.
    """

    camino: list[tuple[int, int]] = field(default_factory=list)
    indice: int = 0


class Documento:
    """Documento en edición, con cursor y deshacer/rehacer por instantáneas."""

    #: Número máximo de instantáneas conservadas para deshacer.
    LIMITE_DESHACER = 200

    def __init__(self) -> None:
        self.raiz: list[Nodo] = []
        self._cursor = _Cursor()
        self._pasado: list[tuple[list[Nodo], _Cursor]] = []
        self._futuro: list[tuple[list[Nodo], _Cursor]] = []

    # --- estado -----------------------------------------------------------

    def secuencia_actual(self) -> list[Nodo]:
        """La secuencia (raíz o hueco) en la que está el cursor."""
        secuencia = self.raiz
        for indice_nodo, indice_hueco in self._cursor.camino:
            nodo = secuencia[indice_nodo]
            assert isinstance(nodo, Estructura)
            secuencia = nodo.huecos[indice_hueco]
        return secuencia

    def camino_cursor(self) -> list[tuple[int, int]]:
        return list(self._cursor.camino)

    def indice_cursor(self) -> int:
        return self._cursor.indice

    def estructura_actual(self) -> Estructura | None:
        """La estructura dentro de cuyo hueco está el cursor, si la hay."""
        if not self._cursor.camino:
            return None
        secuencia = self.raiz
        for indice_nodo, indice_hueco in self._cursor.camino[:-1]:
            nodo = secuencia[indice_nodo]
            assert isinstance(nodo, Estructura)
            secuencia = nodo.huecos[indice_hueco]
        nodo = secuencia[self._cursor.camino[-1][0]]
        assert isinstance(nodo, Estructura)
        return nodo

    def nodo_derecha(self) -> Nodo | None:
        """El nodo inmediatamente a la derecha del cursor, si lo hay."""
        secuencia = self.secuencia_actual()
        if self._cursor.indice < len(secuencia):
            return secuencia[self._cursor.indice]
        return None

    def vacio(self) -> bool:
        return not self.raiz

    # --- edición ----------------------------------------------------------

    def insertar(self, nodo: Nodo) -> None:
        """Inserta un nodo en el cursor; si es estructura, entra al primer hueco."""
        self._guardar_instantanea()
        secuencia = self.secuencia_actual()
        secuencia.insert(self._cursor.indice, nodo)
        if isinstance(nodo, Estructura):
            self._cursor.camino.append((self._cursor.indice, 0))
            self._cursor.indice = 0
        else:
            self._cursor.indice += 1

    def borrar_atras(self) -> Nodo | None:
        """Borra el nodo a la izquierda del cursor y lo devuelve."""
        if self._cursor.indice == 0:
            return None
        self._guardar_instantanea()
        secuencia = self.secuencia_actual()
        self._cursor.indice -= 1
        return secuencia.pop(self._cursor.indice)

    def borrar(self) -> Nodo | None:
        """Borra el nodo a la derecha del cursor y lo devuelve."""
        secuencia = self.secuencia_actual()
        if self._cursor.indice >= len(secuencia):
            return None
        self._guardar_instantanea()
        return secuencia.pop(self._cursor.indice)

    # --- navegación -------------------------------------------------------

    def izquierda(self) -> Nodo | None:
        """Mueve el cursor un nodo a la izquierda; devuelve el nodo cruzado."""
        if self._cursor.indice == 0:
            return None
        self._cursor.indice -= 1
        return self.secuencia_actual()[self._cursor.indice]

    def derecha(self) -> Nodo | None:
        """Mueve el cursor un nodo a la derecha; devuelve el nodo cruzado."""
        secuencia = self.secuencia_actual()
        if self._cursor.indice >= len(secuencia):
            return None
        self._cursor.indice += 1
        return secuencia[self._cursor.indice - 1]

    def inicio(self) -> None:
        self._cursor.indice = 0

    def fin(self) -> None:
        self._cursor.indice = len(self.secuencia_actual())

    def entrar(self) -> Estructura | None:
        """Entra en el primer hueco de la estructura a la derecha del cursor."""
        nodo = self.nodo_derecha()
        if not isinstance(nodo, Estructura):
            return None
        self._cursor.camino.append((self._cursor.indice, 0))
        self._cursor.indice = 0
        return nodo

    def salir(self) -> Estructura | None:
        """Sale de la estructura actual; el cursor queda tras ella."""
        estructura = self.estructura_actual()
        if estructura is None:
            return None
        indice_nodo, _ = self._cursor.camino.pop()
        self._cursor.indice = indice_nodo + 1
        return estructura

    def hueco_siguiente(self) -> int | None:
        """Pasa al siguiente hueco de la estructura actual.

        Devuelve el índice del nuevo hueco; si el cursor estaba en el
        último hueco (o fuera de toda estructura) sale de la estructura,
        como :meth:`salir`, y devuelve ``None``.
        """
        estructura = self.estructura_actual()
        if estructura is None:
            return None
        indice_nodo, indice_hueco = self._cursor.camino[-1]
        if indice_hueco + 1 >= len(estructura.huecos):
            self.salir()
            return None
        self._cursor.camino[-1] = (indice_nodo, indice_hueco + 1)
        self._cursor.indice = 0
        return indice_hueco + 1

    # --- deshacer ---------------------------------------------------------

    def deshacer(self) -> bool:
        if not self._pasado:
            return False
        self._futuro.append(self._instantanea())
        self.raiz, self._cursor = self._pasado.pop()
        return True

    def rehacer(self) -> bool:
        if not self._futuro:
            return False
        self._pasado.append(self._instantanea())
        self.raiz, self._cursor = self._futuro.pop()
        return True

    def _instantanea(self) -> tuple[list[Nodo], _Cursor]:
        return copy.deepcopy((self.raiz, self._cursor))

    def _guardar_instantanea(self) -> None:
        self._pasado.append(self._instantanea())
        del self._pasado[: -self.LIMITE_DESHACER]
        self._futuro.clear()
