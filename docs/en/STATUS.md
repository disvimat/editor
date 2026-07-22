# Project status — what exists and what is missing

**Languages:** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Audit against the module list of the original project brief
([README.md](../BRIEF.es.md)). Updated 2026-07-21.

Legend: **done** · **partial** — usable but incomplete · **pending** — not started.

## Summary

The editor is usable today for **linear arithmetic and elementary algebra**,
on the **desktop** (wxPython + NVDA) and on the **web** (FastAPI + native
MathML), with speech in English, Spanish and French, six-dot braille in
Spanish, XHTML import/export, Unicode braille export and an exact-arithmetic
calculator with a teacher's lock.

The two largest gaps are the **NVDA add-on** (braille displays and direct
speech, modules B3/E1) and **two-dimensional structures** (matrices and
tables, modules A10/B7).

## A) Operating modules

| Module | State | Notes |
|---|---|---|
| A1 Unicode/MathML → DisvimatEditor filter | **done** | Round trip verified by tests |
| A2 signs and structures → key strokes | **done** | `keys_signs.json` |
| A3 commands → key strokes | **partial** | Table done; the *conditions* grammar is not implemented (the `condition` field exists and conditional entries are ignored) |
| A4 alternative keys (numeric keypad) | **partial** | Four bindings only; the full keypad scheme is pending |
| A5 script / add-on designer | **pending** | The core is a clean public API, which is the prerequisite |
| A6 help file (editable, per language) | **pending** | |
| A7 user profile configurator | **partial** | `profiles.json` limits elements per level and locks the calculator; there is no editing interface for profiles |
| A8 calculator | **partial** | Exact fraction arithmetic, precedence, powers and exact roots; no variables, functions or trigonometry |
| A9 calculator locker | **done** | `calculator: false` in the profile (the `exam` profile) |
| A10 two-dimensional structures (tables, matrices, determinants) | **pending** | |
| A11 two-dimensional algorithms | **pending** | |

## B) Presentation modules

| Module | State | Notes |
|---|---|---|
| B1 glyph table | **done** | With linear templates for structures |
| B2 labels / speech per language | **done** | Editing feedback in English, Spanish, French (our tables); whole-expression reading via [MathCAT](MATHCAT.md) for English and Spanish |
| B3 br8 (NVDA and braille displays) | **pending** | Needs a dedicated NVDA add-on; MathCAT's own add-on is the reference |
| B4 graphical presentation window | **done** | Native text control (desktop) and native MathML (web) |
| B5 braille transcriber | **done (external engines)** | Braille comes from a ladder ([BRAILLE.md](BRAILLE.md)): [MathCAT](MATHCAT.md) for math (CMU, UEB), [liblouis](BRAILLE.md) for text (official tables, e.g. French), our `br6` tables as last resort. Verified on 64-bit Python 3.13 |
| B6 br6 window | **partial** | The window shows and follows the transcription; navigating *inside* the braille window is not implemented |
| B7 presentation of 2D structures | **pending** | |
| B8 presentation of 2D algorithms | **pending** | |
| B9 sign-language messages | **pending** | |

## C) Export modules

| Module | State | Notes |
|---|---|---|
| C1 XHTML | **done** | MathML that browsers render and screen readers speak |
| C2 PDF | **pending** | Planned via WeasyPrint, reusing the XHTML export |
| C3 braille export | **done** | Exports Unicode braille (U+2800…, `.brl`, UTF-8) from whichever engine is active (MathCAT / liblouis / tables). ASCII conversion is still available in code but is no longer the export format |
| C4 MP3 | **pending** | |

## D) Import modules

| Module | State | Notes |
|---|---|---|
| D1 XHTML | **done** | Undoable; clear errors for unsupported content |
| D2 LaTeX | **pending** | |

## E) Extension modules

| Module | State |
|---|---|
| E6 internationalisation | **done** — English, Spanish, French; adding a language is editing JSON |
| E1 br8 braille-display input | **pending** |
| E2 virtual braille keyboard | **pending** |
| E3 formula collections | **pending** |
| E4 mathematical dictionary | **pending** |
| E5 theorem store | **pending** |
| E7 handwriting input | **pending** |
| E8 custom symbols | **pending** |
| E9 voice control | **pending** |
| E10–E11 statistical and function graphs | **pending** |
| E12 graph sonification | **pending** |
| E13 interactive exercises | **pending** |
| E14 mathematical games | **pending** |

## F) Chemistry version

All of F1–F6 are **pending**. The groundwork exists: the catalogue already
carries a `category` field, so chemistry signs and structures are added as
data rather than as code.

## Cross-cutting gaps worth knowing

These are not in the original module list but matter for real use:

1. ~~No native document format.~~ **Done:** the `.dvm` format
   ([DOCUMENT.md](DOCUMENT.md)) saves and reopens the exact tree, with the
   language and profile it was written for. Save/Open on desktop and web.
2. ~~A document is a single line.~~ **Done:** documents are now
   **multi-line** — `Return` starts a line, arrow keys move between lines at
   the top level, and each line renders, speaks and brailles on its own.
3. **No NVDA add-on**, so speech relies on the status line (desktop) and on
   the `aria-live` region (web), instead of speaking directly.
4. **Web sessions live in memory** and disappear when the process restarts;
   there is no authentication or persistence.
5. **Braille needs expert validation.** The engine is finished, the values
   are not: they must be checked against the CBE mathematical braille
   standard before any classroom use.
6. **Automated accessibility testing is missing.** Table integrity is
   enforced in CI, but there is no axe-core pass on the web page and no
   scripted NVDA testing; accessibility is verified by hand.

## Suggested next steps

Braille/speech (MathCAT + liblouis) and the document layer (`.dvm`,
multi-line) are done. What remains, in order of impact:

1. NVDA add-on for braille displays and direct speech (B3/E1) — MathCAT's
   own NVDA add-on is the reference implementation to follow.
2. Two-dimensional structures (A10/B7): matrices and tables.
3. PDF (C2) and MP3 (C4) export.
4. Mixed text + mathematics in a document (liblouis text braille then
   covers the prose parts).
