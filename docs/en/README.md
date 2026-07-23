# DISVIMAT — Accessible scientific editor

**Languages:** [English](../en/README.md) · [Español](../es/README.md) · [Français](../fr/README.md)

DISVIMAT is a scientific editor (mathematics, and chemistry later on) for
blind and partially sighted people. It runs **on the desktop** and **on the
web**, sharing one single core, and it presents every expression in four
ways: on screen, as speech, in braille and as exportable files.

- [Architecture](ARCHITECTURE.md) — how the project is built and why.
- [Tables](TABLES.md) — the data that drives the editor's behaviour.
- [Document format](DOCUMENT.md) — multi-line documents and the `.dvm` format.
- [Add-ons](ADDONS.md) — extending the editor without touching the core.
- [Status](STATUS.md) — what is done and what is missing.
- [MathCAT](MATHCAT.md) — the external speech and braille engine.

## Requirements

- Python 3.12 or later.
- For the desktop interface: wxPython (installed automatically).
- Recommended on Windows: the [NVDA](https://www.nvaccess.org/) screen reader.

## Installation

```bash
python -m venv .venv
.venv/bin/pip install -e ".[desktop,web,dev]"   # Windows: .venv\Scripts\pip
```

On Windows you can simply double-click `arrancar.bat`, which creates the
environment the first time and then starts the desktop editor in Spanish.

## Running it

```bash
# Desktop
python -m disvimat.desktop

# Web (then open http://127.0.0.1:8000/)
python -m disvimat.web.app
```

Two environment variables configure both interfaces:

| Variable | Meaning | Values |
|---|---|---|
| `DISVIMAT_LANG` | interface and speech language | `en` (default), `es`, `fr` |
| `DISVIMAT_PROFILE` | user profile (A7) | `beginner`, `intermediate`, `advanced`, `exam` |
| `DISVIMAT_KEYMAP` | keyboard profile — another editor's commands | `lambda`, `edico` (see `data/keymaps/`) |
| `DISVIMAT_ADDONS` | folder of add-on scripts | a path (see [ADDONS](ADDONS.md)) |
| `DISVIMAT_DATA` | table directory | a path; defaults to `data/` |

On the web the language is also a query parameter: `http://127.0.0.1:8000/?language=fr`.

## Speech and the screen reader

The editor **speaks every action** through your screen reader (NVDA, JAWS)
or SAPI: the sign or structure inserted, the blank you moved to, the result
of a calculation, and the word you finish when you press space. It also
pushes the current line to a connected braille display.

That needs `accessible_output2`, which the `[desktop]` extra installs. If it
is missing the editor still works, but the feedback only appears in the
status bar — which a screen reader does not read on its own.

## Keys

Key names are canonical and never translated, so they are the same in
every language and in both interfaces.

| Keys | Action |
|---|---|
| `0-9`, letters | Insert text |
| `+` `-` `*` `/` `=` `<` `>` `%` `,` | Insert the matching sign |
| `Ctrl+F` | Fraction |
| `Ctrl+R` / `Ctrl+Shift+R` | Square root / nth root |
| `Ctrl+P` / `Ctrl+B` | Power / subscript |
| `Tab` | Next slot of the structure |
| `←` `→` `Home` `End` | Move the cursor |
| `↓` `↑` | Enter / leave a structure |
| `Delete` / `Backspace` | Delete (a structure is deleted whole) |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl+L` / `Ctrl+Shift+L` | Read the element / the whole line |
| `Ctrl+Enter` | Calculate the result |
| `Ctrl+I` / `Ctrl+E` | Import / export XHTML (desktop) |
| `Ctrl+6` | Braille window (desktop) |

The numeric keypad also carries `+`, `−`, `×` and `÷` (the latter inserts a
fraction).

## Quick start

Type `1`, `+`, `Ctrl+F`, `2`, `Tab`, `3`. You get `1+(2∕3)` on screen, the
line reads "1 plus fraction 2 over 3 end of fraction", and `Ctrl+Enter`
answers "result: 5/3" as an exact value.

## Developing

```bash
.venv/bin/ruff check .      # linting
.venv/bin/mypy              # strict typing on the core
.venv/bin/pytest            # tests
```

The code base, including identifiers, comments and table keys, is written
**in English** so that anyone can contribute. Everything the user reads or
hears lives in the `data/` tables and is translated there — never in the
code. See [TABLES.md](TABLES.md).

## Licence

GPL-2.0-only. Author: Carlos Daniel Ondo Angue (info@iataccess.org).
