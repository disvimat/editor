"""Carga y validación de las tablas DisvimatEditor (decisión previa "b").

Todas las tablas comparten la misma envoltura JSON::

    {"tabla": "...", "version": 1, "lengua": "es" | null, "entradas": [...]}

y se validan con pydantic al cargarse: una tabla incoherente falla aquí,
con un mensaje claro para el mantenedor, y nunca llega al usuario final.

Convenciones:

- Las pulsaciones (``teclas``) usan los nombres canónicos en inglés que
  emiten wx y el navegador ("Left", "Ctrl+F", "Ctrl+Shift+R"); las
  etiquetas visibles para el usuario se localizan aparte (tabla B2).
- Las tablas dependientes de la lengua llevan sufijo: ``etiquetas.es.json``.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from disvimat.core.elementos import Elemento, Registro, TipoElemento


class EntradaTecla(Registro):
    """A2/A3/A4: correspondencia elemento -> pulsación (con condicionantes)."""

    teclas: str
    condicion: str | None = None


class EntradaGlifo(Registro):
    """B1: glifo con que se presenta un signo o estructura en la edición lineal.

    Las estructuras pueden llevar ``plantilla`` de presentación lineal con
    marcas ``{1}``, ``{2}``... para sus huecos: ``"({1}∕{2})"`` en la fracción.
    Sin plantilla, la presentación es genérica: ``glifo(h1;h2)``.
    """

    glifo: str
    plantilla: str | None = None


#: Partes admitidas en la verbalización lineal de una estructura.
PARTES_VALIDAS = frozenset({"inicio", "separador", "fin"})


class EntradaEtiqueta(Registro):
    """B2: etiqueta textual para listas, línea de estado y síntesis de voz.

    Las estructuras pueden llevar ``partes`` (inicio/separador/fin) para
    la lectura lineal: "fracción ... entre ... fin de fracción".
    """

    etiqueta: str
    partes: dict[str, str] | None = None

    @field_validator("partes")
    @classmethod
    def _claves_de_partes(cls, partes: dict[str, str] | None) -> dict[str, str] | None:
        if partes:
            desconocidas = set(partes) - PARTES_VALIDAS
            if desconocidas:
                raise ValueError(f"partes desconocidas: {sorted(desconocidas)}")
        return partes


class EntradaBraille(Registro):
    """B3/B5: correspondencia de un elemento con celdas braille.

    Una celda se escribe con sus puntos ("1-4-5"; "" es la celda en
    blanco). Los signos llevan ``celdas``; las estructuras llevan
    ``partes`` (inicio/separador/fin), cada una con su lista de celdas.
    """

    celdas: list[str] | None = None
    partes: dict[str, list[str]] | None = None

    @field_validator("partes")
    @classmethod
    def _claves_de_partes(cls, partes: dict[str, list[str]] | None) -> dict[str, list[str]] | None:
        if partes:
            desconocidas = set(partes) - PARTES_VALIDAS
            if desconocidas:
                raise ValueError(f"partes desconocidas: {sorted(desconocidas)}")
        return partes

    @model_validator(mode="after")
    def _algo_que_transcribir(self) -> Self:
        if self.celdas is None and self.partes is None:
            raise ValueError(f"{self.id!r} necesita celdas o partes")
        return self


class EntradaBrailleTexto(Registro):
    """B5: correspondencia de un carácter de texto (letra, dígito) con celdas.

    El ``id`` es descriptivo ("letra_a", "digito_0", "espacio"); la clave
    de búsqueda real es ``caracter``. Tabla dependiente de la lengua.
    """

    caracter: str = Field(min_length=1, max_length=1)
    celdas: list[str] = Field(min_length=1)


class EntradaPerfil(Registro):
    """A7: perfil de usuario; limita los elementos disponibles por nivel.

    ``calculadora`` implementa el bloqueo del profesor (A9): en falso, el
    perfil no puede usar la calculadora.
    """

    nivel: int = Field(ge=1)
    calculadora: bool = True


class EntradaMensaje(Registro):
    """Mensajes del programa para el usuario, localizables por lengua.

    Los produce el núcleo identificados por id (p. ej. los errores de la
    calculadora); el texto vive aquí, nunca en el código.
    """

    texto: str


class Tabla[E: Registro](BaseModel):
    """Envoltura común de todas las tablas DisvimatEditor."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tabla: str
    version: int = Field(ge=1)
    lengua: str | None = None
    entradas: list[E]

    @model_validator(mode="after")
    def _ids_unicos(self) -> Self:
        vistos: set[str] = set()
        for entrada in self.entradas:
            if entrada.id in vistos:
                raise ValueError(f"id duplicado en la tabla {self.tabla!r}: {entrada.id!r}")
            vistos.add(entrada.id)
        return self


def cargar_tabla[E: Registro](ruta: Path, tipo_entrada: type[E]) -> Tabla[E]:
    """Carga y valida una tabla JSON con entradas del tipo indicado."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    modelo: type[Tabla[E]] = Tabla[tipo_entrada]  # type: ignore[valid-type]
    return modelo.model_validate(datos)


class Catalogo:
    """Catálogo de elementos DisvimatEditor con acceso por ``id``."""

    def __init__(self, elementos: list[Elemento]) -> None:
        self._por_id: dict[str, Elemento] = {}
        for elemento in elementos:
            if elemento.id in self._por_id:
                raise ValueError(f"id duplicado en el catálogo: {elemento.id!r}")
            self._por_id[elemento.id] = elemento

    @classmethod
    def cargar(cls, ruta: Path) -> Self:
        """Carga el catálogo desde ``elementos.json`` (misma envoltura común)."""
        return cls(cargar_tabla(ruta, Elemento).entradas)

    def __contains__(self, id_elemento: str) -> bool:
        return id_elemento in self._por_id

    def __getitem__(self, id_elemento: str) -> Elemento:
        return self._por_id[id_elemento]

    def __iter__(self) -> Iterator[Elemento]:
        return iter(self._por_id.values())

    def __len__(self) -> int:
        return len(self._por_id)

    def ids(self) -> set[str]:
        return set(self._por_id)

    def por_tipo(self, tipo: TipoElemento) -> list[Elemento]:
        return [elemento for elemento in self if elemento.tipo is tipo]


def ruta_tabla_lengua(directorio: Path, nombre: str, lengua: str) -> Path:
    """Ruta de una tabla dependiente de la lengua, con reserva al español.

    Busca ``nombre.<lengua>.json``; si no existe, devuelve la versión
    en español, que es la lengua de referencia del proyecto (E6).
    """
    ruta = directorio / f"{nombre}.{lengua}.json"
    if ruta.exists():
        return ruta
    return directorio / f"{nombre}.es.json"


def dir_datos() -> Path:
    """Directorio de las tablas: ``$DISVIMAT_DATOS`` o el ``data/`` del proyecto.

    La resolución relativa al código sirve para la instalación editable
    de desarrollo; las aplicaciones empaquetadas deberán fijar la
    variable de entorno.
    """
    entorno = os.environ.get("DISVIMAT_DATOS")
    if entorno:
        return Path(entorno)
    return Path(__file__).resolve().parents[3] / "data"
