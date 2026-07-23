"""Example add-on: count what is on the current line and say it.

Drop this file (or your own) in a folder and point ``DISVIMAT_ADDONS`` at
it::

    set DISVIMAT_ADDONS=C:\\Users\\me\\disvimat-addons

The editor discovers it at start-up, adds the command to the catalogue,
binds the key stroke and speaks the label in the user's language — with no
change to the editor itself.
"""

from disvimat.core.document import Character, Sign, Structure


def count_line(editor):  # noqa: ANN001, ANN201 - add-ons are plain Python
    """Say how many characters, signs and structures the line holds."""
    line = editor.document.current_line()
    characters = sum(1 for node in line if isinstance(node, Character))
    signs = sum(1 for node in line if isinstance(node, Sign))
    structures = sum(1 for node in line if isinstance(node, Structure))
    return f"{characters} characters, {signs} signs, {structures} structures"


def register(registry):  # noqa: ANN001, ANN201
    """Called by DISVIMAT with the add-on registry."""
    registry.add_command(
        id="count_line",
        run=count_line,
        keys="Ctrl+Alt+C",
        labels={
            "en": "count the line",
            "es": "contar la línea",
            "fr": "compter la ligne",
        },
    )
