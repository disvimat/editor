"""Modelo de los elementos DisvimatEditor (decisión previa "a" del README).

Un elemento es la unidad mínima sobre la que opera el editor: un signo
(sin huecos), una estructura (con huecos, p. ej. una fracción) o un
comando (una acción del editor). El documento en memoria es un árbol
cuyos nodos referencian estos elementos por su ``id``.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Los ids son ASCII, en minúsculas e inmutables: todas las demás tablas
#: (teclas, glifos, etiquetas, braille...) se refieren a ellos.
ID_PATRON = r"^[a-z][a-z0-9_]*$"

#: Elemento del catálogo que representa un hueco vacío (presentación y
#: verbalización); no es editable y no tiene pulsación asignada.
ID_HUECO = "hueco"


class Registro(BaseModel):
    """Base de todo registro de tabla: referencia estable por ``id``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATRON)


class TipoElemento(StrEnum):
    """Tipificación básica de los elementos DisvimatEditor."""

    SIGNO = "signo"
    ESTRUCTURA = "estructura"
    COMANDO = "comando"


class Elemento(Registro):
    """Un elemento del catálogo DisvimatEditor.

    ``mathml`` y ``unicode`` establecen la correspondencia con XHTML
    (filtro A1); ``aridad`` es el número de huecos de una estructura;
    ``nivel`` es el nivel de usuario mínimo en que el elemento está
    disponible (perfiles A7).
    """

    tipo: TipoElemento
    categoria: str
    mathml: str | None = None
    unicode: str | None = None
    aridad: int = Field(default=0, ge=0)
    nivel: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _aridad_coherente(self) -> Self:
        if self.tipo is TipoElemento.ESTRUCTURA and self.aridad < 1:
            raise ValueError(f"la estructura {self.id!r} debe tener aridad >= 1")
        if self.tipo is not TipoElemento.ESTRUCTURA and self.aridad != 0:
            raise ValueError(f"{self.id!r} no es una estructura: su aridad debe ser 0")
        return self
