"""Output ports: how an expression is read aloud and transcribed.

These two protocols are the seam that lets the editor take its speech and
its braille either from our own tables or from an external engine such as
MathCAT, without the rest of the core knowing which one is in use.

The distinction that matters: reading a **whole expression** is a
mathematical-notation problem that specialised engines solve better than
we can, whereas the *editing* feedback ("blank 2", "exit structure:
fraction") is our own user interface and always comes from the label
tables.
"""

from typing import Protocol

from disvimat.core.document import Node


class ExpressionReader(Protocol):
    """Reads a complete expression aloud."""

    def read(self, nodes: list[Node]) -> str:
        """The spoken form of the whole sequence."""
        ...


class BrailleProvider(Protocol):
    """Transcribes an expression into braille."""

    def unicode(self, nodes: list[Node]) -> str:
        """Unicode braille (U+2800...), for the screen and braille displays."""
        ...

    def ascii(self, nodes: list[Node]) -> str:
        """ASCII braille, for the .BRA export (C3)."""
        ...
