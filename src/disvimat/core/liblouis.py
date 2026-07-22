"""Optional liblouis backend for text braille.

`liblouis <https://liblouis.io/>`_ (LGPL-2.1+) is the braille translator
used by NVDA, Orca and most assistive technology. It ships official,
maintained tables for a great many languages, which is exactly why we use
it instead of writing our own character tables.

**Its role here.** liblouis translates *text* to braille; it is not a
math-notation engine. So it handles the literary/text braille (letters,
digits, words), while [MathCAT](mathcat.py) handles the mathematical
notation. That is the same split NVDA uses. In this editor liblouis is the
braille fallback below MathCAT and above our own hand tables, and the
source of official braille for the plain-text parts.

**Availability.** liblouis is not a plain pip install: the ``louis`` Python
module is a ctypes wrapper around the native ``liblouis`` library plus a
tables directory. We load the native library directly with a minimal
ctypes binding (below) so we control the DLL and table paths precisely.
Everything degrades to our tables when the library is absent — see
``scripts/install_liblouis.py`` and ``docs/*/BRAILLE.md``.
"""

import ctypes
import os
import sys
from collections.abc import Callable
from ctypes import POINTER, byref, c_char_p, c_int, c_void_p
from pathlib import Path
from typing import Protocol

from disvimat.core.document import Node
from disvimat.core.transcription.braille import unicode_to_ascii

#: liblouis translation mode: ``dotsIO | ucBrl`` yields Unicode braille
#: (U+2800...) instead of a table's display charset. Validated on 3.38.
_MODE_UNICODE_BRAILLE = 4 | 64

#: Official text table per language. Grade 1 (uncontracted) is the safe
#: default alongside mathematics. Editing this dict is how you retarget a
#: language; the files come from the liblouis tables directory.
TEXT_TABLES: dict[str, str] = {
    "es": "es-g1.ctb",  # Spanish, uncontracted
    "en": "en-ueb-g1.ctb",  # Unified English Braille, uncontracted
    "fr": "fr-bfu-comp6.utb",  # French, 6-dot computer braille
}

#: Environment overrides for the native library and the tables directory.
DLL_ENV = "LIBLOUIS_DLL"
TABLES_ENV = "LOUIS_TABLEPATH"

#: Where ``scripts/install_liblouis.py`` places the library and tables,
#: relative to ``site-packages``.
_INSTALL_SUBDIR = "disvimat_liblouis"


class LiblouisUnavailable(RuntimeError):
    """liblouis cannot be used (library, tables or language missing)."""


class _Native(Protocol):
    """The three liblouis C functions this binding needs."""

    def lou_version(self) -> bytes | int: ...
    def lou_charSize(self) -> int: ...
    def lou_translateString(self, *args: object) -> int: ...


def _install_root() -> Path:
    import sysconfig

    return Path(sysconfig.get_path("platlib")) / _INSTALL_SUBDIR


def find_library_path() -> Path | None:
    """Locate the native liblouis library."""
    override = os.environ.get(DLL_ENV)
    if override and Path(override).is_file():
        return Path(override)
    name = "liblouis.dll" if sys.platform == "win32" else "liblouis.so"
    candidate = _install_root() / "bin" / name
    return candidate if candidate.is_file() else None


def find_tables_dir() -> Path | None:
    """Locate the liblouis tables directory."""
    override = os.environ.get(TABLES_ENV)
    if override and Path(override).is_dir():
        return Path(override)
    candidate = _install_root() / "tables"
    return candidate if candidate.is_dir() else None


class Liblouis:
    """Minimal ctypes binding: load the library and translate text."""

    def __init__(self, library_path: Path, tables_dir: Path) -> None:
        if sys.platform == "win32":
            os.add_dll_directory(str(library_path.parent))
        self._lib: _Native = ctypes.CDLL(str(library_path))
        self._tables_dir = tables_dir
        self._lib.lou_version.restype = c_char_p
        self._lib.lou_charSize.restype = c_int
        # widechar width is a build-time choice (2 or 4 bytes); ask at runtime.
        self._wide = ctypes.c_uint16 if self._lib.lou_charSize() == 2 else ctypes.c_uint32
        self._lib.lou_translateString.restype = c_int
        self._lib.lou_translateString.argtypes = [
            c_char_p,
            POINTER(self._wide),
            POINTER(c_int),
            POINTER(self._wide),
            POINTER(c_int),
            c_void_p,
            c_char_p,
            c_int,
        ]

    def version(self) -> str:
        raw = self._lib.lou_version()
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    def translate(self, table: str, text: str) -> str:
        """Translate ``text`` with ``table`` into Unicode braille."""
        if not text:
            return ""
        table_path = self._tables_dir / table
        in_array = (self._wide * (len(text) + 1))(*[ord(character) for character in text])
        in_len = c_int(len(text))
        capacity = len(text) * 4 + 16
        out_array = (self._wide * capacity)()
        out_len = c_int(capacity)
        ok = self._lib.lou_translateString(
            str(table_path).encode("utf-8"),
            in_array,
            byref(in_len),
            out_array,
            byref(out_len),
            None,
            None,
            _MODE_UNICODE_BRAILLE,
        )
        if not ok:
            raise LiblouisUnavailable(f"liblouis could not translate with {table!r}")
        return "".join(chr(out_array[i]) for i in range(out_len.value))


def load_native(library_path: Path | None = None, tables_dir: Path | None = None) -> Liblouis:
    """Build the binding, or raise :class:`LiblouisUnavailable`."""
    library = library_path or find_library_path()
    tables = tables_dir or find_tables_dir()
    if library is None or tables is None:
        raise LiblouisUnavailable("liblouis library or tables not found")
    return Liblouis(library, tables)


def is_available() -> bool:
    """Whether the native library and tables can be located and loaded."""
    try:
        load_native()
    except (LiblouisUnavailable, OSError):
        return False
    return True


class LiblouisText:
    """Text braille from liblouis, driven by our linearised document.

    Satisfies :class:`~disvimat.core.output.BrailleProvider`.
    """

    def __init__(
        self,
        linearise: Callable[[list[Node]], str],
        language: str,
        *,
        native: Liblouis | None = None,
        table: str | None = None,
    ) -> None:
        self.table = table or TEXT_TABLES.get(language)
        if self.table is None:
            raise LiblouisUnavailable(f"no liblouis text table for {language!r}")
        self._linearise = linearise
        self._native = native if native is not None else load_native()

    def unicode(self, nodes: list[Node]) -> str:
        assert self.table is not None
        return self._native.translate(self.table, self._linearise(nodes))

    def ascii(self, nodes: list[Node]) -> str:
        return unicode_to_ascii(self.unicode(nodes))
