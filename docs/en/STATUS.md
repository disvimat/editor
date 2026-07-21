# Project status — what exists and what is missing

**Languages:** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Audit against the module list of the original project brief
([README.md](../BRIEF.es.md)). Updated 2026-07-21.

Legend: **done** · **partial** — usable but incomplete · **pending** — not started.

## Summary

The editor is usable today for **linear arithmetic and elementary algebra**,
on the **desktop** (wxPython + NVDA) and on the **web** (FastAPI + native
MathML), with speech in English, Spanish and French, six-dot braille in
Spanish, XHTML import/export, .BRA export and an exact-arithmetic
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
| B2 labels / speech per language | **done** | English, Spanish and French |
| B3 br8 (NVDA and braille displays) | **pending** | Needs a dedicated NVDA add-on |
| B4 graphical presentation window | **done** | Native text control (desktop) and native MathML (web) |
| B5 br6 transcriber | **partial** | The engine is table-driven and complete; **the Spanish cell values are provisional and must be reviewed against the CBE standard**; no English (UEB) or French (NMB) tables |
| B6 br6 window | **partial** | The window shows and follows the transcription; navigating *inside* the braille window is not implemented |
| B7 presentation of 2D structures | **pending** | |
| B8 presentation of 2D algorithms | **pending** | |
| B9 sign-language messages | **pending** | |

## C) Export modules

| Module | State | Notes |
|---|---|---|
| C1 XHTML | **done** | MathML that browsers render and screen readers speak |
| C2 PDF | **pending** | Planned via WeasyPrint, reusing the XHTML export |
| C3 BRA (six-dot braille) | **partial** | Works; depends on the braille table review, and the ASCII encoding is the provisional NABCC one |
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

1. **No native document format.** There is no "save" / "open": documents
   travel through XHTML import and export only. A `.dvm` format that keeps
   the tree, the language and the profile is needed.
2. **A document is a single line.** The tree holds one expression sequence;
   there are no paragraphs, several lines or mixed text and mathematics.
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

1. Review the braille tables with a braille specialist (B5/C3) — cheap,
   high impact, and it is only data.
2. NVDA add-on for braille displays and direct speech (B3/E1).
3. Native document format with save and open, plus multi-line documents.
4. Two-dimensional structures (A10/B7): matrices and tables.
5. PDF (C2) and MP3 (C4) export.
