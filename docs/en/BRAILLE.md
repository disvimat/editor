# Braille — how it is produced

**Languages:** [English](../en/BRAILLE.md) · [Español](../es/BRAILLE.md) · [Français](../fr/BRAILLE.md)

DISVIMAT does not hand-write braille tables. It uses the same two engines
that assistive technology like NVDA uses, each for what it is best at, with
a graceful fallback:

```
math braille   →  MathCAT      (CMU, UEB, Nemeth…)   ┐
text braille   →  liblouis     (official tables)     ├─ ladder, in order
last resort    →  our tables   (br6.*.json)          ┘
```

## Why two engines

- **[MathCAT](MATHCAT.md)** reads mathematical *notation* (MathML) and
  produces normative math braille — CMU for Spanish, UEB for English. This
  is the right braille for the expressions the editor is made of.
- **liblouis** translates *text* to braille with official, maintained
  tables for a great many languages. It is the standard braille translator
  behind NVDA, Orca and BrailleBlaster. It handles the literary/text parts
  and gives braille for languages MathCAT does not cover (for example
  French text braille).

They are complementary, not alternatives — NVDA itself uses both. In this
editor MathCAT provides the braille for a whole math expression; liblouis
is the text-braille layer below it; our own `br6` tables (whose Spanish
values are provisional) are only the last resort when neither engine is
installed.

## The ladder in code

`create_outputs` in [`backends.py`](../../src/disvimat/backends.py) picks
the braille engine per language:

1. MathCAT if installed and it covers the language.
2. else liblouis if installed and it has a text table for the language.
3. else our `br6` tables.
4. else braille is disabled for that language (never another language's).

Each layer is its own adapter behind the `BrailleProvider` port
([`core/output.py`](../../src/disvimat/core/output.py)):
[`core/mathcat.py`](../../src/disvimat/core/mathcat.py),
[`core/liblouis.py`](../../src/disvimat/core/liblouis.py),
[`core/transcription/braille.py`](../../src/disvimat/core/transcription/braille.py).

## Installing liblouis

liblouis is not a plain pip install — it is a native library plus a tables
directory. For 64-bit Windows there is a one-command installer:

```bash
python scripts/install_liblouis.py
```

It downloads the official `liblouis.dll` and the tables into
`site-packages/disvimat_liblouis/`, then verifies a Spanish translation.
On Linux/macOS install liblouis from the package manager
(`apt install liblouis`, `brew install liblouis`) and point
`LIBLOUIS_DLL` and `LOUIS_TABLEPATH` at the library and its tables.

Verify:

```python
from disvimat.core.liblouis import is_available
print(is_available())          # True once library and tables are found
```

## Table selection

The text table used per language is a small, editable map in
`core/liblouis.py` (`TEXT_TABLES`): Spanish → `es-g1.ctb`, English →
`en-ueb-g1.ctb`, French → `fr-bfu-comp6.utb`. Grade 1 (uncontracted) is the
safe default next to mathematics. Retargeting a language, or adding one, is
editing that map — the tables themselves are liblouis's, not ours.

## Things to know

- **Verified** on 64-bit Python 3.13 (Windows): liblouis produces Unicode
  braille (`dotsIO | ucBrl` mode) with official tables — Spanish `es-g1`,
  English `en-ueb-g1`, French `fr-bfu-comp6`.
- **liblouis is a text engine.** Feeding it a whole math expression would
  braille the symbols literally, which is why math braille goes through
  MathCAT instead. liblouis matters for the text parts and as the fallback,
  and for text-only languages.
- **Determinism in tests.** `DISVIMAT_NO_LIBLOUIS=1` (and
  `DISVIMAT_NO_MATHCAT=1`) force our tables even when the engines are
  installed; the test suite sets both so results are identical with or
  without the native libraries.
