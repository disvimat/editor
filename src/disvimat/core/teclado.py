"""Resolución de pulsaciones según las tablas A2/A3 (y A4 en el futuro).

Las pulsaciones llegan de la interfaz ya normalizadas al formato canónico
de las tablas ("+", "Left", "Ctrl+F", "Ctrl+Shift+R").
"""

from disvimat.core.elementos import Elemento
from disvimat.core.tablas import Catalogo, EntradaTecla, Tabla


class Teclado:
    """Traduce una pulsación canónica al elemento del catálogo asignado."""

    def __init__(self, catalogo: Catalogo, *tablas: Tabla[EntradaTecla]) -> None:
        self._por_teclas: dict[str, Elemento] = {}
        for tabla in tablas:
            for entrada in tabla.entradas:
                # Los condicionantes de A3 tienen su gramática pendiente
                # (Fase 2); de momento solo cargan las entradas incondicionales.
                if entrada.condicion is None:
                    self._por_teclas[entrada.teclas] = catalogo[entrada.id]

    def resolver(self, teclas: str) -> Elemento | None:
        return self._por_teclas.get(teclas)
