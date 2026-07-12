"""Comprobaciones de integridad entre tablas.

Las usan los tests (la CI falla si una tabla es incoherente: principio 5
del plan) y las usará el editor de tablas (decisión previa "c") para
avisar de los conflictos antes de guardar.
"""

from disvimat.core.elementos import Registro, TipoElemento
from disvimat.core.tablas import Catalogo, EntradaTecla, Tabla


def ids_desconocidos[R: Registro](tabla: Tabla[R], catalogo: Catalogo) -> set[str]:
    """Ids referenciados por la tabla que no existen en el catálogo."""
    return {entrada.id for entrada in tabla.entradas} - catalogo.ids()


def ids_sin_cubrir[R: Registro](
    tabla: Tabla[R], catalogo: Catalogo, tipos: set[TipoElemento]
) -> set[str]:
    """Elementos del catálogo de los tipos dados sin entrada en la tabla."""
    cubiertos = {entrada.id for entrada in tabla.entradas}
    return {elemento.id for elemento in catalogo if elemento.tipo in tipos} - cubiertos


def conflictos_de_teclas(*tablas: Tabla[EntradaTecla]) -> dict[str, list[str]]:
    """Pulsaciones asignadas a más de un elemento con la misma condición.

    Acepta varias tablas para detectar también los conflictos entre
    ellas (p. ej. una pulsación usada a la vez por un signo de A2 y un
    comando de A3). Devuelve ``{pulsación: [ids en conflicto]}``.
    """
    por_pulsacion: dict[tuple[str, str | None], list[str]] = {}
    for tabla in tablas:
        for entrada in tabla.entradas:
            clave = (entrada.teclas, entrada.condicion)
            por_pulsacion.setdefault(clave, []).append(entrada.id)
    return {
        teclas if condicion is None else f"{teclas} [{condicion}]": ids
        for (teclas, condicion), ids in por_pulsacion.items()
        if len(ids) > 1
    }
