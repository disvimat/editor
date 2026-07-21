"""Interface strings, localised with a table like everything else (E6).

The project deliberately uses one single localisation mechanism: JSON
tables per language with a fallback to the reference language. Interface
strings therefore live in ``ui.<language>.json`` next to the labels and
messages, so translators work with one format and no compilation step is
needed (unlike gettext, which requires building ``.mo`` files).
"""

from pathlib import Path

from disvimat.core.tables import MessageEntry, Table, data_dir, language_table_path, load_table


class UIText:
    """Interface strings for one language, with placeholder substitution."""

    def __init__(self, strings: dict[str, str]) -> None:
        self._strings = strings

    @classmethod
    def load(cls, directory: Path | None = None, language: str = "en") -> "UIText":
        directory = directory or data_dir()
        table: Table[MessageEntry] = load_table(
            language_table_path(directory, "ui", language), MessageEntry
        )
        return cls({entry.id: entry.text for entry in table.entries})

    def __call__(self, string_id: str, **placeholders: object) -> str:
        """The localised string; unknown ids fall back to the id itself."""
        text = self._strings.get(string_id, string_id)
        if placeholders:
            for name, value in placeholders.items():
                text = text.replace("{" + name + "}", str(value))
        return text
