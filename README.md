# DISVIMAT — Accessible scientific editor

A scientific editor for blind and partially sighted people. It runs on the
**desktop** and on the **web** from a single core, and presents every
expression on screen, as speech, in braille, and as exportable files.

**Documentation:**
[English](docs/en/README.md) ·
[Español](docs/es/README.md) ·
[Français](docs/fr/README.md)

| | English | Español | Français |
|---|---|---|---|
| Overview and usage | [README](docs/en/README.md) | [README](docs/es/README.md) | [README](docs/fr/README.md) |
| How it is built | [ARCHITECTURE](docs/en/ARCHITECTURE.md) | [ARCHITECTURE](docs/es/ARCHITECTURE.md) | [ARCHITECTURE](docs/fr/ARCHITECTURE.md) |
| Changing it without code | [TABLES](docs/en/TABLES.md) | [TABLES](docs/es/TABLES.md) | [TABLES](docs/fr/TABLES.md) |
| What is done, what is missing | [STATUS](docs/en/STATUS.md) | [STATUS](docs/es/STATUS.md) | [STATUS](docs/fr/STATUS.md) |
| External speech and braille engine | [MATHCAT](docs/en/MATHCAT.md) | [MATHCAT](docs/es/MATHCAT.md) | [MATHCAT](docs/fr/MATHCAT.md) |

The original project brief, in Spanish, is preserved at
[docs/BRIEF.es.md](docs/BRIEF.es.md); it is the source of the module
numbering (A1, B5, C3…) used throughout the documentation.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -e ".[desktop,web,dev]"   # Windows: .venv\Scripts\pip

python -m disvimat.desktop     # desktop editor
python -m disvimat.web.app     # web editor at http://127.0.0.1:8000/
```

Windows users can double-click `arrancar.bat`, which prepares the
environment on first run and starts the desktop editor in Spanish.

Type `1`, `+`, `Ctrl+F`, `2`, `Tab`, `3` and you get `1+(2∕3)`, read aloud
as "1 plus fraction 2 over 3 end of fraction"; `Ctrl+Enter` computes it.

## Two things contributors should know

**The code base is in English** — identifiers, comments, table keys and
element ids — so that anyone can contribute. Everything the *user* reads or
hears is not in the code at all: it lives in the `data/` tables and is
translated there. The editor currently speaks English, Spanish and French.

**Behaviour is data, not code.** Which key inserts which sign, how a
fraction is drawn, spoken and transcribed into braille: all of it is JSON
under `data/`. Adding a sign or a language means editing a table, and the
integrity tests will tell you if anything is missing. See
[TABLES](docs/en/TABLES.md).

## Development

```bash
.venv/bin/ruff check .      # linting
.venv/bin/mypy              # strict typing on the core
.venv/bin/pytest            # tests
```

Branch workflow: work happens on a topic branch, is merged into `dev` for
testing (continuous integration plus manual NVDA checks), and only reaches
`main` once validated.

> **Braille notice.** Our own braille engine is complete, but the Spanish
> cell values are **provisional**. The project integrates
> [MathCAT](docs/en/MATHCAT.md) (DAISY), which implements the normative CMU
> code; once its binding is built, MathCAT provides the braille and our
> tables become the fallback. Braille never falls back across languages:
> a language with no braille source has its braille features disabled
> rather than showing another country's braille.

## Licence

GPL-2.0-only. Author: Carlos Daniel Ondo Angue (info@iataccess.org).
