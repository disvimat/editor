# MathCAT integration

**Languages:** [English](../en/MATHCAT.md) · [Español](../es/MATHCAT.md) · [Français](../fr/MATHCAT.md)

[MathCAT](https://daisy.github.io/MathCAT/) (DAISY, MIT licence) turns
MathML into speech and braille. Adopting it matters to this project for
one reason above all: **it implements CMU**, the *Código Matemático
Unificado*, the Spanish mathematical braille standard — maintained by
braille specialists, unlike our own tables, which are explicitly
provisional.

## Why it fits

Our core already produces MathML (module C1), and MathML is precisely what
MathCAT consumes. So MathCAT plugs into the two output ports defined in
[`core/output.py`](../../src/disvimat/core/output.py) without the document,
the keyboard or the calculator knowing anything about it.

| | Source |
|---|---|
| Reading a whole expression | MathCAT if available, our `labels` tables otherwise |
| Braille (screen, display, `.BRA`) | MathCAT if available, our `br6` tables otherwise |
| **Editing feedback** ("blank 2", "exit structure: fraction") | **always our tables** |

That last row is the important distinction: MathCAT reads mathematical
*notation*; it does not narrate an editing session. Both kinds of speech
are needed and they come from different places.

## What MathCAT does and does not cover

- **Braille codes:** Nemeth, UEB Technical, **CMU**, Vietnamese,
  German/Austrian LaTeX, ASCIIMath.
- **Speech:** English, German, Spanish, Finnish, Indonesian, Norwegian,
  Swedish, Vietnamese, Chinese (Traditional). **There is no French**, so
  French keeps using our tables entirely.
- **Navigation:** MathCAT navigates a *static* expression; our editor needs
  an editing cursor that inserts and deletes. The two models are different,
  so MathCAT navigation is not used for editing.

## Current state

The **seam is implemented and tested**; the **binding is not built yet**.

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — the adapter:
  sets `Language`, `SpeechStyle` and `BrailleCode`, hands over our MathML
  and returns speech and braille.
- [`backends.py`](../../src/disvimat/backends.py) — the policy: MathCAT
  leads, tables are the fallback.
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — drives the
  adapter with a fake library, so everything on our side of the boundary is
  verified.

Because MathCAT is absent today, the application runs exactly as before on
our tables. Installing the binding is enough to switch it over; no code
changes are needed.

## Building the Python binding

MathCAT is **not published on PyPI**, and the binary shipped with the NVDA
add-on is built for 32-bit Python 3.11 (NVDA's interpreter), so it cannot
be imported by an ordinary 64-bit Python. The binding has to be built:

1. Install the [Rust toolchain](https://rustup.rs/).
2. Clone [daisy/MathCATForPython](https://github.com/daisy/MathCATForPython)
   and build it for your Python version and architecture (it is a PyO3
   project; follow the build instructions in that repository).
3. Put the resulting module (`libmathcat_py`) on the Python path of the
   environment running DISVIMAT.
4. Make the **Rules** directory available. MathCAT looks for it in the path
   given to `SetRulesDir`, then in the `MathCATRulesDir` environment
   variable, then next to the binary. Our adapter accepts a `rules_dir`
   argument for the first option.

Verify it with:

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True once the binding is importable
```

and then:

```python
from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

Two details to confirm on a real build, because they could not be tested
without the library: the exact module name (we try `libmathcat_py` then
`libmathcat`) and the braille code strings (`"CMU"`, `"UEB"`). Both are
single constants at the top of `core/mathcat.py`.

## Braille policy

Once MathCAT is available its braille wins for Spanish, and our `br6`
tables stay as the fallback for when it is not installed and for languages
it does not cover. Braille never falls back across languages: a language
with no braille source simply has its braille features disabled.
