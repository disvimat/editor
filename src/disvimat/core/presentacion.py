"""Presentación lineal del documento con glifos (tablas B1, ventana B4).

Convierte el árbol en una cadena de texto y calcula el offset del cursor
dentro de ella, para que la interfaz coloque el caret. Los huecos vacíos
se presentan con el glifo del elemento ``hueco``.
"""

import re

from disvimat.core.documento import Caracter, Documento, Estructura, Nodo, Signo
from disvimat.core.elementos import ID_HUECO
from disvimat.core.tablas import EntradaGlifo, Tabla

_MARCA_HUECO = re.compile(r"\{(\d+)\}")


class Presentador:
    """Render lineal del documento según la tabla de glifos."""

    def __init__(self, glifos: Tabla[EntradaGlifo]) -> None:
        self._glifos = {entrada.id: entrada.glifo for entrada in glifos.entradas}
        self._plantillas = {
            entrada.id: entrada.plantilla for entrada in glifos.entradas if entrada.plantilla
        }

    def render(self, documento: Documento) -> tuple[str, int]:
        """Texto lineal completo y offset del cursor dentro de él."""
        texto, posicion = self._secuencia(
            documento.raiz, documento.camino_cursor(), documento.indice_cursor()
        )
        assert posicion is not None, "el cursor no apareció durante el render"
        return texto, posicion

    def glifo(self, id_elemento: str) -> str:
        return self._glifos.get(id_elemento, "?")

    # --- interno ------------------------------------------------------------

    def _secuencia(
        self, nodos: list[Nodo], camino: list[tuple[int, int]], indice: int
    ) -> tuple[str, int | None]:
        """Renderiza una secuencia; el cursor está aquí si ``camino`` es vacío."""
        partes: list[str] = []
        posicion: int | None = None
        nodo_objetivo = camino[0][0] if camino else None
        for i, nodo in enumerate(nodos):
            if not camino and i == indice:
                posicion = sum(map(len, partes))
            if i == nodo_objetivo:
                assert isinstance(nodo, Estructura)
                texto, sub = self._estructura_con_cursor(nodo, camino, indice)
                if sub is not None:
                    posicion = sum(map(len, partes)) + sub
            else:
                texto = self._nodo(nodo)
            partes.append(texto)
        if not camino and indice == len(nodos):
            posicion = sum(map(len, partes))
        return "".join(partes), posicion

    def _estructura_con_cursor(
        self, estructura: Estructura, camino: list[tuple[int, int]], indice: int
    ) -> tuple[str, int | None]:
        hueco_objetivo = camino[0][1]
        partes: list[str] = []
        posicion: int | None = None
        for trozo in self._trozos(estructura):
            if isinstance(trozo, str):
                partes.append(trozo)
                continue
            hueco = estructura.huecos[trozo]
            if trozo == hueco_objetivo:
                if hueco or camino[1:]:
                    texto, sub = self._secuencia(hueco, camino[1:], indice)
                else:
                    # hueco vacío con el cursor dentro: caret sobre el glifo de hueco
                    texto, sub = self.glifo(ID_HUECO), 0
                if sub is not None:
                    posicion = sum(map(len, partes)) + sub
            else:
                texto = self._hueco(hueco)
            partes.append(texto)
        return "".join(partes), posicion

    def _nodo(self, nodo: Nodo) -> str:
        match nodo:
            case Caracter(texto=texto):
                return texto
            case Signo(id_elemento=id_elemento):
                return self.glifo(id_elemento)
            case Estructura():
                return "".join(
                    trozo if isinstance(trozo, str) else self._hueco(nodo.huecos[trozo])
                    for trozo in self._trozos(nodo)
                )

    def _hueco(self, nodos: list[Nodo]) -> str:
        if not nodos:
            return self.glifo(ID_HUECO)
        return "".join(self._nodo(nodo) for nodo in nodos)

    def _trozos(self, estructura: Estructura) -> list[str | int]:
        """Descompone la plantilla en literales e índices de hueco (base 0)."""
        plantilla = self._plantillas.get(estructura.id_elemento)
        if plantilla is None:
            interior = ";".join(f"{{{n + 1}}}" for n in range(len(estructura.huecos)))
            plantilla = f"{self.glifo(estructura.id_elemento)}({interior})"
        trozos: list[str | int] = []
        fin_anterior = 0
        for marca in _MARCA_HUECO.finditer(plantilla):
            if marca.start() > fin_anterior:
                trozos.append(plantilla[fin_anterior : marca.start()])
            trozos.append(int(marca.group(1)) - 1)
            fin_anterior = marca.end()
        if fin_anterior < len(plantilla):
            trozos.append(plantilla[fin_anterior:])
        return trozos
