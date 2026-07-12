"""Verbalización del documento con las etiquetas B2 (voz y línea de estado).

Las estructuras se leen linealmente con sus ``partes``:
"fracción, 1, entre, 2, fin de fracción". Los caracteres contiguos se
agrupan para que la síntesis lea "123" y no "1, 2, 3".
"""

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.elementos import ID_HUECO
from disvimat.core.tablas import EntradaEtiqueta, Tabla


class Verbalizador:
    """Lectura textual de nodos y secuencias según la tabla de etiquetas."""

    def __init__(self, etiquetas: Tabla[EntradaEtiqueta]) -> None:
        self._entradas = {entrada.id: entrada for entrada in etiquetas.entradas}

    def etiqueta(self, id_elemento: str) -> str:
        entrada = self._entradas.get(id_elemento)
        return entrada.etiqueta if entrada else id_elemento

    def nodo(self, nodo: Nodo) -> str:
        match nodo:
            case Caracter(texto=texto):
                return texto
            case Signo(id_elemento=id_elemento):
                return self.etiqueta(id_elemento)
            case Estructura():
                return self._estructura(nodo)

    def secuencia(self, nodos: list[Nodo]) -> str:
        if not nodos:
            return self.etiqueta(ID_HUECO)
        partes: list[str] = []
        anterior_era_caracter = False
        for nodo in nodos:
            if isinstance(nodo, Caracter) and anterior_era_caracter:
                partes[-1] += nodo.texto
            else:
                partes.append(self.nodo(nodo))
            anterior_era_caracter = isinstance(nodo, Caracter)
        return " ".join(partes)

    def _estructura(self, estructura: Estructura) -> str:
        entrada = self._entradas.get(estructura.id_elemento)
        if entrada is not None and entrada.partes is not None:
            # con partes, el inicio es opcional: "x elevado a 2" no lleva prefijo
            partes = entrada.partes
            inicio = partes.get("inicio", "")
        else:
            partes = {}
            inicio = self.etiqueta(estructura.id_elemento)
        separador = partes.get("separador", "")
        fin = partes.get("fin", "")
        trozos = [inicio] if inicio else []
        for numero, hueco in enumerate(estructura.huecos):
            if numero > 0 and separador:
                trozos.append(separador)
            trozos.append(self.secuencia(hueco))
        if fin:
            trozos.append(fin)
        return " ".join(trozos)
