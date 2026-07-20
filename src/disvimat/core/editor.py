"""Controlador del editor lineal: une teclado, documento y presentaciones.

Las interfaces (escritorio y web) son deliberadamente delgadas: envían
pulsaciones canónicas o caracteres y reflejan el :class:`Resultado`
(texto lineal, posición del caret y verbalización). Toda la lógica de
comportamiento vive aquí y en las tablas de ``data/``.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from disvimat.core.calculadora import Calculadora, ErrorDeCalculo
from disvimat.core.documento import Caracter, Documento, Estructura, Nodo, Signo
from disvimat.core.elementos import ID_HUECO, TipoElemento
from disvimat.core.presentacion import Presentador
from disvimat.core.tablas import (
    Catalogo,
    EntradaEtiqueta,
    EntradaGlifo,
    EntradaMensaje,
    EntradaPerfil,
    EntradaTecla,
    Tabla,
    cargar_tabla,
    dir_datos,
    ruta_tabla_lengua,
)
from disvimat.core.teclado import Teclado
from disvimat.core.verbalizacion import Verbalizador

#: Id de mensaje del bloqueo del profesor (A9); vive en la tabla mensajes.
MSG_CALCULADORA_BLOQUEADA = "calculadora_bloqueada"


@dataclass(frozen=True)
class Resultado:
    """Lo que la interfaz debe reflejar tras cada acción."""

    texto: str
    posicion: int
    verbalizacion: str


class Editor:
    """Editor lineal DisvimatEditor sobre un documento en memoria."""

    def __init__(
        self,
        catalogo: Catalogo,
        teclado: Teclado,
        presentador: Presentador,
        verbalizador: Verbalizador,
        calculadora: Calculadora,
        mensajes: dict[str, str],
        *,
        calculadora_permitida: bool = True,
    ) -> None:
        self.catalogo = catalogo
        self.documento = Documento()
        self._teclado = teclado
        self._presentador = presentador
        self._verbalizador = verbalizador
        self._calculadora = calculadora
        self._mensajes = mensajes
        self._calculadora_permitida = calculadora_permitida
        self._comandos: dict[str, Callable[[], str]] = {
            "izquierda": self._cmd_izquierda,
            "derecha": self._cmd_derecha,
            "inicio_linea": self._cmd_inicio_linea,
            "fin_linea": self._cmd_fin_linea,
            "entrar_estructura": self._cmd_entrar,
            "salir_estructura": self._cmd_salir,
            "siguiente_hueco": self._cmd_hueco_siguiente,
            "borrar": self._cmd_borrar,
            "borrar_atras": self._cmd_borrar_atras,
            "deshacer": self._cmd_deshacer,
            "rehacer": self._cmd_rehacer,
            "leer_elemento": self._leer_actual,
            "leer_linea": self._cmd_leer_linea,
            "calcular": self._cmd_calcular,
        }

    # --- API para las interfaces -------------------------------------------

    def pulsar(self, teclas: str) -> Resultado | None:
        """Ejecuta la pulsación según las tablas; None si no está asignada."""
        elemento = self._teclado.resolver(teclas)
        if elemento is None:
            return None
        if elemento.tipo is TipoElemento.COMANDO:
            comando = self._comandos.get(elemento.id)
            if comando is None:
                return None
            return self._resultado(comando())
        if elemento.tipo is TipoElemento.ESTRUCTURA:
            self.documento.insertar(Estructura(elemento.id, [[] for _ in range(elemento.aridad)]))
            etiqueta = self._verbalizador.etiqueta(elemento.id)
            return self._resultado(f"{etiqueta}, {self._verbalizador.etiqueta(ID_HUECO)} 1")
        self.documento.insertar(Signo(elemento.id))
        return self._resultado(self._verbalizador.etiqueta(elemento.id))

    def escribir(self, caracter: str) -> Resultado:
        """Inserta un carácter de texto plano (dígitos, letras, espacio)."""
        self.documento.insertar(Caracter(caracter))
        return self._resultado(caracter)

    def estado(self) -> Resultado:
        """El estado actual sin ejecutar ninguna acción (lectura de línea)."""
        return self._resultado(self._cmd_leer_linea())

    def cargar(self, nodos: list[Nodo]) -> Resultado:
        """Sustituye el contenido del documento (importaciones D); deshacible."""
        self.documento.cargar(nodos)
        return self._resultado(self._cmd_leer_linea())

    # --- comandos ------------------------------------------------------------

    def _cmd_izquierda(self) -> str:
        nodo = self.documento.izquierda()
        if nodo is None:
            return self._verbalizador.etiqueta("inicio_linea")
        return self._verbalizador.nodo(nodo)

    def _cmd_derecha(self) -> str:
        nodo = self.documento.derecha()
        if nodo is None:
            return self._verbalizador.etiqueta("fin_linea")
        return self._verbalizador.nodo(nodo)

    def _cmd_inicio_linea(self) -> str:
        self.documento.inicio()
        return self._verbalizador.etiqueta("inicio_linea")

    def _cmd_fin_linea(self) -> str:
        self.documento.fin()
        return self._verbalizador.etiqueta("fin_linea")

    def _cmd_entrar(self) -> str:
        estructura = self.documento.entrar()
        if estructura is None:
            return self._leer_actual()
        etiqueta = self._verbalizador.etiqueta("entrar_estructura")
        return f"{etiqueta}: {self._verbalizador.etiqueta(estructura.id_elemento)}"

    def _cmd_salir(self) -> str:
        estructura = self.documento.salir()
        if estructura is None:
            return self._leer_actual()
        etiqueta = self._verbalizador.etiqueta("salir_estructura")
        return f"{etiqueta}: {self._verbalizador.etiqueta(estructura.id_elemento)}"

    def _cmd_hueco_siguiente(self) -> str:
        estructura = self.documento.estructura_actual()
        if estructura is None:
            return self._leer_actual()
        numero_hueco = self.documento.hueco_siguiente()
        if numero_hueco is None:
            etiqueta = self._verbalizador.etiqueta("salir_estructura")
            return f"{etiqueta}: {self._verbalizador.etiqueta(estructura.id_elemento)}"
        return f"{self._verbalizador.etiqueta(ID_HUECO)} {numero_hueco + 1}"

    def _cmd_borrar(self) -> str:
        nodo = self.documento.borrar()
        if nodo is None:
            return self._leer_actual()
        return f"{self._verbalizador.etiqueta('borrar')}: {self._verbalizador.nodo(nodo)}"

    def _cmd_borrar_atras(self) -> str:
        nodo = self.documento.borrar_atras()
        if nodo is None:
            return self._verbalizador.etiqueta("inicio_linea")
        return f"{self._verbalizador.etiqueta('borrar_atras')}: {self._verbalizador.nodo(nodo)}"

    def _cmd_deshacer(self) -> str:
        self.documento.deshacer()
        return f"{self._verbalizador.etiqueta('deshacer')}: {self._cmd_leer_linea()}"

    def _cmd_rehacer(self) -> str:
        self.documento.rehacer()
        return f"{self._verbalizador.etiqueta('rehacer')}: {self._cmd_leer_linea()}"

    def _cmd_calcular(self) -> str:
        """Calcula la expresión (A8), respetando el bloqueo del profesor (A9)."""
        if not self._calculadora_permitida:
            return self._mensaje(MSG_CALCULADORA_BLOQUEADA)
        try:
            valor = self._calculadora.evaluar(self.documento.raiz)
        except ErrorDeCalculo as error:
            return self._mensaje(error.id_mensaje)
        return f"{self._verbalizador.etiqueta('calcular')}: {valor}"

    def _cmd_leer_linea(self) -> str:
        return self._verbalizador.secuencia(self.documento.raiz)

    def _mensaje(self, id_mensaje: str) -> str:
        return self._mensajes.get(id_mensaje, id_mensaje)

    def _leer_actual(self) -> str:
        nodo = self.documento.nodo_derecha()
        if nodo is None:
            return self._verbalizador.etiqueta("fin_linea")
        return self._verbalizador.nodo(nodo)

    def _resultado(self, verbalizacion: str) -> Resultado:
        texto, posicion = self._presentador.render(self.documento)
        return Resultado(texto=texto, posicion=posicion, verbalizacion=verbalizacion)


def crear_editor(
    directorio: Path | None = None, lengua: str = "es", perfil: str | None = None
) -> Editor:
    """Construye un editor cargando todas las tablas del directorio de datos.

    ``lengua`` resuelve las tablas dependientes de la lengua (con reserva
    al español, E6); ``perfil`` limita los elementos por nivel (A7).
    """
    directorio = directorio or dir_datos()
    catalogo = Catalogo.cargar(directorio / "elementos.json")
    nivel: int | None = None
    calculadora_permitida = True
    if perfil is not None:
        perfiles: Tabla[EntradaPerfil] = cargar_tabla(directorio / "perfiles.json", EntradaPerfil)
        por_id = {entrada.id: entrada for entrada in perfiles.entradas}
        if perfil not in por_id:
            raise ValueError(f"perfil desconocido: {perfil!r}")
        nivel = por_id[perfil].nivel
        calculadora_permitida = por_id[perfil].calculadora
    tablas_de_teclas: list[Tabla[EntradaTecla]] = [
        cargar_tabla(directorio / nombre, EntradaTecla)
        for nombre in ("teclas_signos.json", "teclas_comandos.json", "teclas_numpad.json")
    ]
    glifos: Tabla[EntradaGlifo] = cargar_tabla(directorio / "glifos.json", EntradaGlifo)
    etiquetas: Tabla[EntradaEtiqueta] = cargar_tabla(
        ruta_tabla_lengua(directorio, "etiquetas", lengua), EntradaEtiqueta
    )
    mensajes_tabla: Tabla[EntradaMensaje] = cargar_tabla(
        ruta_tabla_lengua(directorio, "mensajes", lengua), EntradaMensaje
    )
    mensajes = {entrada.id: entrada.texto for entrada in mensajes_tabla.entradas}
    return Editor(
        catalogo,
        Teclado(catalogo, *tablas_de_teclas, nivel=nivel),
        Presentador(glifos),
        Verbalizador(etiquetas),
        Calculadora(),
        mensajes,
        calculadora_permitida=calculadora_permitida,
    )
