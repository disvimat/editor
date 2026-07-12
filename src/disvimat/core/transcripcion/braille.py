"""Transcripción braille de 6 puntos dirigida por tablas (módulo B5).

Todo el conocimiento braille vive en las tablas por lengua:
``br6.<lengua>.json`` (elementos del catálogo, con partes para las
estructuras) y ``br6_texto.<lengua>.json`` (letras y dígitos). El
transcriptor solo aplica las reglas generales: prefijo de número una vez
por cada grupo de dígitos y prefijo de mayúscula por letra mayúscula.

Salidas: braille unicode (ventana B6 y líneas braille) y braille ASCII
para la exportación .BRA (C3).
"""

from pathlib import Path

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo
from disvimat.core.elementos import ID_HUECO
from disvimat.core.tablas import (
    EntradaBraille,
    EntradaBrailleTexto,
    Tabla,
    cargar_tabla,
    dir_datos,
    ruta_tabla_lengua,
)

#: Ids de servicio que la tabla br6 debe definir (además de los elementos).
ID_PREFIJO_NUMERO = "prefijo_numero"
ID_MAYUSCULA = "mayuscula"

#: Braille ASCII norteamericano (NABCC), indexado por el valor de los
#: puntos 1..6. Es la codificación provisional de la exportación .BRA;
#: cuando se disponga de la tabla de la CBE, se sustituye aquí.
_ASCII_BRAILLE = " a1b'k2l@cif/msp\"e3h9o6r^djg>ntq,*5<-u8v.%[$+x!&;:4\\0z7(_?w]#y)="

#: Celda de relleno para lo que no tiene transcripción (todos los puntos).
_CELDA_DESCONOCIDA = 0b111111


def _celda(patron: str) -> int:
    """Convierte "1-4-5" en la máscara de puntos; "" es la celda en blanco."""
    valor = 0
    if patron:
        for punto in patron.split("-"):
            valor |= 1 << (int(punto) - 1)
    return valor


def _celdas(patrones: list[str]) -> list[int]:
    return [_celda(patron) for patron in patrones]


class Transcriptor:
    """Transcribe el árbol del documento a braille según las tablas."""

    def __init__(self, elementos: Tabla[EntradaBraille], texto: Tabla[EntradaBrailleTexto]) -> None:
        self._por_elemento: dict[str, list[int]] = {}
        self._partes: dict[str, dict[str, list[int]]] = {}
        for entrada in elementos.entradas:
            if entrada.celdas is not None:
                self._por_elemento[entrada.id] = _celdas(entrada.celdas)
            if entrada.partes is not None:
                self._partes[entrada.id] = {
                    parte: _celdas(patrones) for parte, patrones in entrada.partes.items()
                }
        self._por_caracter = {
            entrada.caracter: _celdas(entrada.celdas) for entrada in texto.entradas
        }

    # --- salidas -------------------------------------------------------------

    def unicode(self, nodos: list[Nodo]) -> str:
        """Braille unicode (U+2800...) para pantalla y línea braille."""
        return "".join(chr(0x2800 + celda) for celda in self.celdas(nodos))

    def ascii(self, nodos: list[Nodo]) -> str:
        """Braille ASCII para la exportación .BRA (C3)."""
        return "".join(_ASCII_BRAILLE[celda] for celda in self.celdas(nodos))

    def celdas(self, nodos: list[Nodo]) -> list[int]:
        """Las celdas (máscaras de puntos 1..6) de la secuencia completa."""
        resultado: list[int] = []
        self._secuencia(nodos, resultado)
        return resultado

    # --- interno -------------------------------------------------------------

    def _secuencia(self, nodos: list[Nodo], salida: list[int]) -> None:
        en_numero = False
        for nodo in nodos:
            if isinstance(nodo, Caracter):
                en_numero = self._caracter(nodo.texto, salida, en_numero)
                continue
            en_numero = False
            if isinstance(nodo, Signo):
                salida.extend(self._elemento(nodo.id_elemento))
            else:
                self._estructura(nodo, salida)

    def _caracter(self, caracter: str, salida: list[int], en_numero: bool) -> bool:
        if caracter.isdigit():
            if not en_numero:
                salida.extend(self._elemento(ID_PREFIJO_NUMERO))
            salida.extend(self._por_caracter.get(caracter, [_CELDA_DESCONOCIDA]))
            return True
        if caracter.isupper() and caracter.lower() in self._por_caracter:
            salida.extend(self._elemento(ID_MAYUSCULA))
            salida.extend(self._por_caracter[caracter.lower()])
        else:
            salida.extend(self._por_caracter.get(caracter, [_CELDA_DESCONOCIDA]))
        return False

    def _estructura(self, estructura: Estructura, salida: list[int]) -> None:
        partes = self._partes.get(estructura.id_elemento, {})
        salida.extend(partes.get("inicio", []))
        for numero, hueco in enumerate(estructura.huecos):
            if numero > 0:
                salida.extend(partes.get("separador", []))
            if hueco:
                self._secuencia(hueco, salida)
            else:
                salida.extend(self._elemento(ID_HUECO))
        salida.extend(partes.get("fin", []))

    def _elemento(self, id_elemento: str) -> list[int]:
        return self._por_elemento.get(id_elemento, [_CELDA_DESCONOCIDA])


def crear_transcriptor(directorio: Path | None = None, lengua: str = "es") -> Transcriptor:
    """Construye el transcriptor con las tablas br6 de la lengua indicada."""
    directorio = directorio or dir_datos()
    elementos: Tabla[EntradaBraille] = cargar_tabla(
        ruta_tabla_lengua(directorio, "br6", lengua), EntradaBraille
    )
    texto: Tabla[EntradaBrailleTexto] = cargar_tabla(
        ruta_tabla_lengua(directorio, "br6_texto", lengua), EntradaBrailleTexto
    )
    return Transcriptor(elementos, texto)
