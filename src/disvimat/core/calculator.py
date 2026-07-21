"""Calculator bound to the editor (module A8; lock A9 through profiles).

Evaluates the document expression with exact fraction arithmetic
(``fractions.Fraction``); only non-exact roots are approximated. Errors
are identified by message id and localised through the
``messages.<language>.json`` table — this module holds no user-facing
text.
"""

from fractions import Fraction

from disvimat.core.document import Character, Node, Sign, Structure

#: Message ids produced by the calculator (``messages`` table).
MSG_NOT_COMPUTABLE = "expression_not_computable"
MSG_DIVISION_BY_ZERO = "division_by_zero"

_Token = tuple[str, Fraction | str]


class CalculationError(Exception):
    """The expression cannot be computed; ``message_id`` localises why."""

    def __init__(self, message_id: str) -> None:
        super().__init__(message_id)
        self.message_id = message_id


class Calculator:
    """Evaluates sequences of DisvimatEditor nodes."""

    def __init__(self, decimal_separator: str = ",") -> None:
        self._decimal_separator = decimal_separator

    def evaluate(self, nodes: list[Node]) -> str:
        """The value of the expression, formatted to present and speak."""
        return self._format(self._value(nodes))

    # --- parsing --------------------------------------------------------------

    def _value(self, nodes: list[Node]) -> Fraction:
        tokens = self._tokens(nodes)
        value, position = self._sum(tokens, 0)
        if position != len(tokens):
            raise CalculationError(MSG_NOT_COMPUTABLE)
        return value

    def _tokens(self, nodes: list[Node]) -> list[_Token]:
        tokens: list[_Token] = []
        digits = ""
        decimals: int | None = None

        def flush_number() -> None:
            nonlocal digits, decimals
            if not digits:
                if decimals is not None:
                    raise CalculationError(MSG_NOT_COMPUTABLE)
                return
            whole = int(digits)
            scale = 10 ** (decimals or 0)
            tokens.append(("number", Fraction(whole, scale)))
            digits, decimals = "", None

        for node in nodes:
            if isinstance(node, Character):
                if node.text.isdigit():
                    digits += node.text
                    if decimals is not None:
                        decimals += 1
                    continue
                if node.text == " ":
                    flush_number()
                    continue
                raise CalculationError(MSG_NOT_COMPUTABLE)
            if isinstance(node, Sign):
                if node.element_id == "decimal_point":
                    if not digits or decimals is not None:
                        raise CalculationError(MSG_NOT_COMPUTABLE)
                    decimals = 0
                    continue
                flush_number()
                if node.element_id in ("plus", "minus", "times", "divide"):
                    tokens.append(("operator", node.element_id))
                    continue
                raise CalculationError(MSG_NOT_COMPUTABLE)
            flush_number()
            tokens.append(("number", self._structure(node)))
        flush_number()
        return tokens

    # --- grammar: sum -> product -> unit ---------------------------------------

    def _sum(self, tokens: list[_Token], position: int) -> tuple[Fraction, int]:
        value, position = self._product(tokens, position)
        while position < len(tokens) and tokens[position][1] in ("plus", "minus"):
            operator = tokens[position][1]
            following, position = self._product(tokens, position + 1)
            value = value + following if operator == "plus" else value - following
        return value, position

    def _product(self, tokens: list[_Token], position: int) -> tuple[Fraction, int]:
        value, position = self._unit(tokens, position)
        while position < len(tokens) and tokens[position][1] in ("times", "divide"):
            operator = tokens[position][1]
            following, position = self._unit(tokens, position + 1)
            if operator == "divide":
                if following == 0:
                    raise CalculationError(MSG_DIVISION_BY_ZERO)
                value = value / following
            else:
                value = value * following
        return value, position

    def _unit(self, tokens: list[_Token], position: int) -> tuple[Fraction, int]:
        if position < len(tokens) and tokens[position][0] == "operator":
            operator = tokens[position][1]
            if operator in ("plus", "minus"):
                value, position = self._unit(tokens, position + 1)
                return (value if operator == "plus" else -value), position
        if position >= len(tokens) or tokens[position][0] != "number":
            raise CalculationError(MSG_NOT_COMPUTABLE)
        content = tokens[position][1]
        assert isinstance(content, Fraction)
        return content, position + 1

    # --- structures --------------------------------------------------------------

    def _structure(self, structure: Structure) -> Fraction:
        identifier = structure.element_id
        if identifier == "fraction":
            numerator = self._value(structure.slots[0])
            denominator = self._value(structure.slots[1])
            if denominator == 0:
                raise CalculationError(MSG_DIVISION_BY_ZERO)
            return numerator / denominator
        if identifier == "power":
            base = self._value(structure.slots[0])
            exponent = self._value(structure.slots[1])
            if exponent.denominator != 1:
                raise CalculationError(MSG_NOT_COMPUTABLE)
            try:
                return base ** int(exponent)
            except ZeroDivisionError as error:
                raise CalculationError(MSG_DIVISION_BY_ZERO) from error
        if identifier == "sqrt":
            return self._root(self._value(structure.slots[0]), 2)
        if identifier == "nth_root":
            index = self._value(structure.slots[1])
            if index.denominator != 1 or index <= 0:
                raise CalculationError(MSG_NOT_COMPUTABLE)
            return self._root(self._value(structure.slots[0]), int(index))
        raise CalculationError(MSG_NOT_COMPUTABLE)

    def _root(self, value: Fraction, index: int) -> Fraction:
        if value < 0:
            raise CalculationError(MSG_NOT_COMPUTABLE)
        approximate = float(value) ** (1.0 / index)
        whole = Fraction(round(approximate))
        if whole**index == value:
            return whole
        return Fraction(approximate).limit_denominator(10**9)

    # --- presentation ------------------------------------------------------------

    def _format(self, value: Fraction) -> str:
        if value.denominator == 1:
            return str(value.numerator)
        text = f"{float(value):.10f}".rstrip("0").rstrip(".")
        return text.replace(".", self._decimal_separator)
