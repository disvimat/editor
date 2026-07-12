"""Filtro A1: MathML (XHTML) → árbol DisvimatEditor.

La correspondencia se toma del catálogo: los ``<mo>`` se resuelven por el
campo ``unicode`` de los signos y los elementos de estructura
(``mfrac``, ``msup``...) por el campo ``mathml``. Un contenido sin
correspondencia produce :class:`ErrorDeFiltro` con un mensaje claro
(la "previsión de nuevos signos" del README llegará en la Fase 2).
"""

import xml.etree.ElementTree as ET

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.elementos import TipoElemento
from disvimat.core.tablas import Catalogo


class ErrorDeFiltro(ValueError):
    """El MathML contiene algo sin correspondencia DisvimatEditor."""


def _nombre(elemento: ET.Element) -> str:
    """Nombre del elemento sin el espacio de nombres MathML."""
    return elemento.tag.rpartition("}")[2]


class FiltroMathML:
    """Convierte expresiones MathML en secuencias de nodos DisvimatEditor."""

    def __init__(self, catalogo: Catalogo) -> None:
        self._catalogo = catalogo
        self._signos_por_unicode = {
            elemento.unicode: elemento.id
            for elemento in catalogo.por_tipo(TipoElemento.SIGNO)
            if elemento.unicode
        }
        self._estructuras_por_mathml = {
            elemento.mathml: elemento
            for elemento in catalogo.por_tipo(TipoElemento.ESTRUCTURA)
            if elemento.mathml
        }

    def desde_texto(self, texto_xml: str) -> list[Nodo]:
        """Convierte un fragmento ``<math>...</math>`` en nodos."""
        try:
            raiz = ET.fromstring(texto_xml)
        except ET.ParseError as error:
            raise ErrorDeFiltro(f"MathML mal formado: {error}") from error
        return self._secuencia(raiz)

    def desde_xhtml(self, texto_xhtml: str) -> list[Nodo]:
        """Extrae la primera expresión ``<math>`` de un documento XHTML (D1)."""
        try:
            raiz = ET.fromstring(texto_xhtml)
        except ET.ParseError as error:
            raise ErrorDeFiltro(f"XHTML mal formado: {error}") from error
        for elemento in raiz.iter():
            if _nombre(elemento) == "math":
                return self._secuencia(elemento)
        raise ErrorDeFiltro("el documento no contiene ninguna expresión <math>")

    # --- interno ------------------------------------------------------------

    def _secuencia(self, contenedor: ET.Element) -> list[Nodo]:
        nodos: list[Nodo] = []
        for hijo in contenedor:
            nodos.extend(self._nodos(hijo))
        return nodos

    def _nodos(self, elemento: ET.Element) -> list[Nodo]:
        nombre = _nombre(elemento)
        if nombre == "mrow":
            return self._secuencia(elemento)
        if nombre in ("mn", "mi", "mtext"):
            return [Caracter(caracter) for caracter in (elemento.text or "").strip()]
        if nombre == "mo":
            texto = (elemento.text or "").strip()
            id_signo = self._signos_por_unicode.get(texto)
            if id_signo is None:
                raise ErrorDeFiltro(f"signo sin correspondencia DisvimatEditor: {texto!r}")
            return [Signo(id_signo)]
        if nombre == "msqrt":
            # msqrt no tiene envoltorio de hueco: sus hijos son el contenido
            return [self._estructura(nombre, [self._secuencia(elemento)])]
        elemento_catalogo = self._estructuras_por_mathml.get(nombre)
        if elemento_catalogo is None:
            raise ErrorDeFiltro(f"elemento MathML sin correspondencia: <{nombre}>")
        hijos = list(elemento)
        if len(hijos) != elemento_catalogo.aridad:
            raise ErrorDeFiltro(
                f"<{nombre}> tiene {len(hijos)} hijos y se esperaban {elemento_catalogo.aridad}"
            )
        return [self._estructura(nombre, [self._nodos(hijo) for hijo in hijos])]

    def _estructura(self, nombre_mathml: str, huecos: list[list[Nodo]]) -> Estructura:
        elemento = self._estructuras_por_mathml.get(nombre_mathml)
        if elemento is None:
            raise ErrorDeFiltro(f"elemento MathML sin correspondencia: <{nombre_mathml}>")
        return Estructura(elemento.id, huecos)
