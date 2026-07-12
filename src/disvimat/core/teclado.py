"""Resolución de pulsaciones según las tablas A2/A3 (y A4 en el futuro).

Las pulsaciones llegan de la interfaz ya normalizadas al formato canónico
de las tablas ("+", "Left", "Ctrl+F", "Ctrl+Shift+R").
"""

from disvimat.core.elementos import Elemento, TipoElemento
from disvimat.core.tablas import Catalogo, EntradaTecla, Tabla


class Teclado:
    """Traduce una pulsación canónica al elemento del catálogo asignado.

    Con ``nivel`` (perfiles A7), los signos y estructuras de nivel
    superior quedan sin asignar; los comandos siempre están disponibles.
    """

    def __init__(
        self, catalogo: Catalogo, *tablas: Tabla[EntradaTecla], nivel: int | None = None
    ) -> None:
        self._nivel = nivel
        self._por_teclas: dict[str, Elemento] = {}
        for tabla in tablas:
            for entrada in tabla.entradas:
                # La gramática de los condicionantes de A3 está pendiente;
                # de momento solo cargan las entradas incondicionales.
                if entrada.condicion is None:
                    self._por_teclas[entrada.teclas] = catalogo[entrada.id]

    def resolver(self, teclas: str) -> Elemento | None:
        elemento = self._por_teclas.get(teclas)
        if (
            elemento is not None
            and elemento.tipo is not TipoElemento.COMANDO
            and self._nivel is not None
            and elemento.nivel > self._nivel
        ):
            return None
        return elemento
