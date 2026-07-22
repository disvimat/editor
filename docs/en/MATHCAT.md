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

## Installing it

MathCAT is **not on PyPI**, but the project publishes prebuilt binaries
(built with PyO3 abi3, so one build serves every Python 3.x). For 64-bit
Python on Windows or Linux there is a one-command installer:

```bash
python scripts/install_mathcat.py
```

It downloads the matching `libmathcat_py` binary and MathCAT's `Rules`
directory into `site-packages`, then verifies the install. After that the
editor uses MathCAT automatically — no code or configuration changes.

Verify by hand with:

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True once binding and rules are present

from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

For a platform with no prebuilt binary (e.g. 32-bit, or a Python the
release does not cover), build from source: install the
[Rust toolchain](https://rustup.rs/), clone
[daisy/MathCATForPython](https://github.com/daisy/MathCATForPython) and
build it (a PyO3 project), then place `libmathcat_py` and a `Rules`
directory on the Python path.

## How it is wired

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — the adapter.
  `SetRulesDir` is called **first** (MathCAT requires it before any
  preference), then `Language`, `SpeechStyle` and `BrailleCode`; it locates
  the rules via the `MATHCAT_RULES_DIR` variable or a `Rules` folder next
  to the binding.
- [`backends.py`](../../src/disvimat/backends.py) — the policy: MathCAT
  leads, tables are the fallback. Set `DISVIMAT_NO_MATHCAT=1` to force the
  tables even when MathCAT is installed (the test suite does this so results
  do not depend on whether MathCAT is present).
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — drives the
  adapter with a fake library, so the boundary is covered without needing
  the real binding.

## Things to know

- **Verified working** on 64-bit Python 3.13 (Windows): Spanish reads
  "1 más 2 tercios" and produces CMU braille; English uses UEB. When
  MathCAT is absent the editor runs on our tables exactly as before.
- **French.** MathCAT ships French *rules*, but they are incomplete (they
  fall back to English for many expressions), so we keep French on our own
  tables for now. When the French rules mature, adding `"fr"` to
  `SPEECH_LANGUAGES` is the only change needed.
- **Global singleton.** The MathCAT binding holds one global configuration
  per process. That is fine for the desktop (one language per run). On the
  web, concurrent sessions in *different* languages could interfere; a
  single-language deployment avoids it. A per-process lock or worker
  affinity is the fix if multi-language web use becomes important.

## Braille policy

Once MathCAT is available its braille wins for Spanish, and our `br6`
tables stay as the fallback for when it is not installed and for languages
it does not cover. Braille never falls back across languages: a language
with no braille source simply has its braille features disabled.
