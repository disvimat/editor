"""Exportación C1: árbol DisvimatEditor → MathML / documento XHTML.

Es la operación inversa del filtro A1: los signos salen como ``<mo>``
con su ``unicode`` de catálogo, las estructuras como su elemento
``mathml``, y los dígitos y letras se agrupan en ``<mn>`` y ``<mi>``.
"""

import xml.etree.ElementTree as ET

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.tablas import Catalogo

MATHML_NS = "http://www.w3.org/1998/Math/MathML"

_PLANTILLA_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{lengua}" xml:lang="{lengua}">
<head>
<meta charset="utf-8"/>
<title>{titulo}</title>
</head>
<body>
<p>{mathml}</p>
</body>
</html>
"""


class ExportadorXHTML:
    """Genera MathML y documentos XHTML a partir del árbol del editor."""

    def __init__(self, catalogo: Catalogo) -> None:
        self._catalogo = catalogo

    def mathml(self, nodos: list[Nodo]) -> ET.Element:
        """Elemento ``<math>`` con el contenido de la secuencia."""
        math = ET.Element("math", {"xmlns": MATHML_NS, "display": "block"})
        self._rellenar(math, nodos)
        return math

    def documento_xhtml(
        self, nodos: list[Nodo], titulo: str = "Documento DISVIMAT", lengua: str = "es"
    ) -> str:
        """Documento XHTML completo con la expresión como MathML."""
        texto_math = ET.tostring(self.mathml(nodos), encoding="unicode")
        return _PLANTILLA_XHTML.format(titulo=titulo, lengua=lengua, mathml=texto_math)

    # --- interno ------------------------------------------------------------

    def _rellenar(self, padre: ET.Element, nodos: list[Nodo]) -> None:
        indice = 0
        while indice < len(nodos):
            nodo = nodos[indice]
            if isinstance(nodo, Caracter):
                indice = self._caracteres(padre, nodos, indice)
                continue
            if isinstance(nodo, Signo):
                simbolo = self._catalogo[nodo.id_elemento].unicode
                if simbolo is None:
                    raise ValueError(f"el signo {nodo.id_elemento!r} no tiene unicode")
                ET.SubElement(padre, "mo").text = simbolo
            else:
                self._estructura(padre, nodo)
            indice += 1

    def _caracteres(self, padre: ET.Element, nodos: list[Nodo], indice: int) -> int:
        """Agrupa dígitos consecutivos en ``<mn>``; las letras van en ``<mi>``."""
        nodo = nodos[indice]
        assert isinstance(nodo, Caracter)
        if nodo.texto.isdigit():
            fin = indice
            while (
                fin < len(nodos) and isinstance(nodos[fin], Caracter) and nodos[fin].texto.isdigit()  # type: ignore[union-attr]
            ):
                fin += 1
            digitos = "".join(n.texto for n in nodos[indice:fin] if isinstance(n, Caracter))
            ET.SubElement(padre, "mn").text = digitos
            return fin
        ET.SubElement(padre, "mi").text = nodo.texto
        return indice + 1

    def _estructura(self, padre: ET.Element, estructura: Estructura) -> None:
        elemento = self._catalogo[estructura.id_elemento]
        if elemento.mathml is None:
            raise ValueError(
                f"la estructura {estructura.id_elemento!r} no tiene correspondencia MathML"
            )
        contenedor = ET.SubElement(padre, elemento.mathml)
        if elemento.mathml == "msqrt":
            # msqrt no lleva envoltorio de hueco: el contenido va directo
            self._rellenar(contenedor, estructura.huecos[0])
            return
        for hueco in estructura.huecos:
            self._hueco(contenedor, hueco)

    def _hueco(self, padre: ET.Element, nodos: list[Nodo]) -> None:
        """Un hueco es un único hijo: se envuelve en ``<mrow>`` si hace falta."""
        temporal = ET.Element("temporal")
        self._rellenar(temporal, nodos)
        hijos = list(temporal)
        if len(hijos) == 1:
            padre.append(hijos[0])
        else:
            mrow = ET.SubElement(padre, "mrow")
            mrow.extend(hijos)
