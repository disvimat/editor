"""Calculadora ligada al editor (módulo A8; bloqueo A9 vía perfiles).

Evalúa la expresión del documento con aritmética exacta de fracciones
(``fractions.Fraction``); solo las raíces no exactas se aproximan. Los
errores se identifican por id de mensaje y se localizan con la tabla
``mensajes.<lengua>.json`` — este módulo no contiene texto para el
usuario.
"""

from fractions import Fraction

from disvimat.core.documento import Caracter, Estructura, Nodo, Signo

#: Ids de mensaje que produce la calculadora (tabla ``mensajes``).
MSG_NO_CALCULABLE = "expresion_no_calculable"
MSG_DIVISION_CERO = "division_entre_cero"

_Token = tuple[str, Fraction | str]


class ErrorDeCalculo(Exception):
    """La expresión no se puede calcular; ``id_mensaje`` localiza el motivo."""

    def __init__(self, id_mensaje: str) -> None:
        super().__init__(id_mensaje)
        self.id_mensaje = id_mensaje


class Calculadora:
    """Evalúa secuencias de nodos DisvimatEditor."""

    def __init__(self, separador_decimal: str = ",") -> None:
        self._coma = separador_decimal

    def evaluar(self, nodos: list[Nodo]) -> str:
        """El valor de la expresión, formateado para presentar y verbalizar."""
        return self._formatear(self._valor(nodos))

    # --- análisis -------------------------------------------------------------

    def _valor(self, nodos: list[Nodo]) -> Fraction:
        tokens = self._tokens(nodos)
        valor, posicion = self._suma(tokens, 0)
        if posicion != len(tokens):
            raise ErrorDeCalculo(MSG_NO_CALCULABLE)
        return valor

    def _tokens(self, nodos: list[Nodo]) -> list[_Token]:
        tokens: list[_Token] = []
        digitos = ""
        decimales: int | None = None

        def volcar_numero() -> None:
            nonlocal digitos, decimales
            if not digitos:
                if decimales is not None:
                    raise ErrorDeCalculo(MSG_NO_CALCULABLE)
                return
            entero = int(digitos)
            escala = 10 ** (decimales or 0)
            tokens.append(("numero", Fraction(entero, escala)))
            digitos, decimales = "", None

        for nodo in nodos:
            if isinstance(nodo, Caracter):
                if nodo.texto.isdigit():
                    digitos += nodo.texto
                    if decimales is not None:
                        decimales += 1
                    continue
                if nodo.texto == " ":
                    volcar_numero()
                    continue
                raise ErrorDeCalculo(MSG_NO_CALCULABLE)
            if isinstance(nodo, Signo):
                if nodo.id_elemento == "coma_decimal":
                    if not digitos or decimales is not None:
                        raise ErrorDeCalculo(MSG_NO_CALCULABLE)
                    decimales = 0
                    continue
                volcar_numero()
                if nodo.id_elemento in ("mas", "menos", "por", "entre"):
                    tokens.append(("operador", nodo.id_elemento))
                    continue
                raise ErrorDeCalculo(MSG_NO_CALCULABLE)
            volcar_numero()
            tokens.append(("numero", self._estructura(nodo)))
        volcar_numero()
        return tokens

    # --- gramática: suma -> producto -> unidad ---------------------------------

    def _suma(self, tokens: list[_Token], posicion: int) -> tuple[Fraction, int]:
        valor, posicion = self._producto(tokens, posicion)
        while posicion < len(tokens) and tokens[posicion][1] in ("mas", "menos"):
            operador = tokens[posicion][1]
            siguiente, posicion = self._producto(tokens, posicion + 1)
            valor = valor + siguiente if operador == "mas" else valor - siguiente
        return valor, posicion

    def _producto(self, tokens: list[_Token], posicion: int) -> tuple[Fraction, int]:
        valor, posicion = self._unidad(tokens, posicion)
        while posicion < len(tokens) and tokens[posicion][1] in ("por", "entre"):
            operador = tokens[posicion][1]
            siguiente, posicion = self._unidad(tokens, posicion + 1)
            if operador == "entre":
                if siguiente == 0:
                    raise ErrorDeCalculo(MSG_DIVISION_CERO)
                valor = valor / siguiente
            else:
                valor = valor * siguiente
        return valor, posicion

    def _unidad(self, tokens: list[_Token], posicion: int) -> tuple[Fraction, int]:
        if posicion < len(tokens) and tokens[posicion][0] == "operador":
            operador = tokens[posicion][1]
            if operador in ("mas", "menos"):
                valor, posicion = self._unidad(tokens, posicion + 1)
                return (valor if operador == "mas" else -valor), posicion
        if posicion >= len(tokens) or tokens[posicion][0] != "numero":
            raise ErrorDeCalculo(MSG_NO_CALCULABLE)
        contenido = tokens[posicion][1]
        assert isinstance(contenido, Fraction)
        return contenido, posicion + 1

    # --- estructuras ------------------------------------------------------------

    def _estructura(self, estructura: Estructura) -> Fraction:
        identificador = estructura.id_elemento
        if identificador == "fraccion":
            numerador = self._valor(estructura.huecos[0])
            denominador = self._valor(estructura.huecos[1])
            if denominador == 0:
                raise ErrorDeCalculo(MSG_DIVISION_CERO)
            return numerador / denominador
        if identificador == "potencia":
            base = self._valor(estructura.huecos[0])
            exponente = self._valor(estructura.huecos[1])
            if exponente.denominator != 1:
                raise ErrorDeCalculo(MSG_NO_CALCULABLE)
            try:
                return base ** int(exponente)
            except ZeroDivisionError as error:
                raise ErrorDeCalculo(MSG_DIVISION_CERO) from error
        if identificador == "raiz":
            return self._raiz(self._valor(estructura.huecos[0]), 2)
        if identificador == "raiz_indice":
            indice = self._valor(estructura.huecos[1])
            if indice.denominator != 1 or indice <= 0:
                raise ErrorDeCalculo(MSG_NO_CALCULABLE)
            return self._raiz(self._valor(estructura.huecos[0]), int(indice))
        raise ErrorDeCalculo(MSG_NO_CALCULABLE)

    def _raiz(self, valor: Fraction, indice: int) -> Fraction:
        if valor < 0:
            raise ErrorDeCalculo(MSG_NO_CALCULABLE)
        aproximado = float(valor) ** (1.0 / indice)
        entero = Fraction(round(aproximado))
        if entero**indice == valor:
            return entero
        return Fraction(aproximado).limit_denominator(10**9)

    # --- presentación ------------------------------------------------------------

    def _formatear(self, valor: Fraction) -> str:
        if valor.denominator == 1:
            return str(valor.numerator)
        texto = f"{float(valor):.10f}".rstrip("0").rstrip(".")
        return texto.replace(".", self._coma)
