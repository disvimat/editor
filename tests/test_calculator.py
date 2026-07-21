"""Calculator A8: exact evaluation and localised errors; lock A9."""

from pathlib import Path

import pytest

from disvimat.core.calculator import (
    MSG_DIVISION_BY_ZERO,
    MSG_NOT_COMPUTABLE,
    CalculationError,
    Calculator,
)
from disvimat.core.document import Character, Node, Sign, Structure
from disvimat.core.editor import create_editor

DATA = Path(__file__).resolve().parents[1] / "data"


def digits(text: str) -> list[Node]:
    return [Character(character) for character in text]


def type_all(editor, strokes: list[str]) -> None:  # type: ignore[no-untyped-def]
    for stroke in strokes:
        if editor.press(stroke) is None and len(stroke) == 1:
            editor.type_character(stroke)


def test_operator_precedence() -> None:
    # 2 + 3 * 4 = 14
    nodes = [*digits("2"), Sign("plus"), *digits("3"), Sign("times"), *digits("4")]
    assert Calculator().evaluate(nodes) == "14"


def test_exact_fraction() -> None:
    # 1/2 + 1/2 = 1, with no floating point drift
    nodes: list[Node] = [
        Structure("fraction", [digits("1"), digits("2")]),
        Sign("plus"),
        Structure("fraction", [digits("1"), digits("2")]),
    ]
    assert Calculator().evaluate(nodes) == "1"


def test_decimal_with_comma() -> None:
    # 1,5 * 2 = 3
    nodes = [*digits("1"), Sign("decimal_point"), *digits("5"), Sign("times"), *digits("2")]
    assert Calculator().evaluate(nodes) == "3"


def test_exact_power_and_root() -> None:
    assert Calculator().evaluate([Structure("power", [digits("2"), digits("10")])]) == "1024"
    assert Calculator().evaluate([Structure("sqrt", [digits("9")])]) == "3"


def test_unary_minus() -> None:
    # -3 + 5 = 2
    nodes = [Sign("minus"), *digits("3"), Sign("plus"), *digits("5")]
    assert Calculator().evaluate(nodes) == "2"


def test_division_by_zero() -> None:
    nodes = [*digits("1"), Sign("divide"), *digits("0")]
    with pytest.raises(CalculationError) as info:
        Calculator().evaluate(nodes)
    assert info.value.message_id == MSG_DIVISION_BY_ZERO


def test_incomplete_expression_is_not_computable() -> None:
    nodes = [*digits("1"), Sign("plus")]
    with pytest.raises(CalculationError) as info:
        Calculator().evaluate(nodes)
    assert info.value.message_id == MSG_NOT_COMPUTABLE


def test_calculate_command_in_the_editor() -> None:
    editor = create_editor(DATA)
    type_all(editor, ["2", "+", "3", "*", "4"])
    result = editor.press("Ctrl+Return")
    assert result is not None
    assert result.speech == "result: 14"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "division by zero"),
        ("es", "división entre cero"),
        ("fr", "division par zéro"),
    ],
)
def test_calculation_errors_are_localised(language: str, expected: str) -> None:
    editor = create_editor(DATA, language=language)
    type_all(editor, ["1", "/", "0"])
    result = editor.press("Ctrl+Return")
    assert result is not None
    assert result.speech == expected


def test_teacher_lock() -> None:
    editor = create_editor(DATA, profile="exam")
    editor.type_character("2")
    result = editor.press("Ctrl+Return")
    assert result is not None
    assert result.speech == "calculator locked"
