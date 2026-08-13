# Architecture

**Languages:** [English](../en/ARCHITECTURE.md) · [Español](../es/ARCHITECTURE.md) · [Français](../fr/ARCHITECTURE.md)

## The one idea to remember

Almost all of the editor's behaviour is **data, not code**. Which key
inserts which sign, how a fraction is drawn, how it is spoken, how it is
transcribed into braille: all of it lives in JSON tables under `data/`.
Adding a sign, changing a shortcut or translating the editor into another
language means editing a table, not writing Python.

That was the request of the original brief — "a single table format, a
single table editor" — and it is the backbone of the design.

## Layers

The project uses a hexagonal (ports and adapters) architecture: a core in
pure Python that knows nothing about interfaces, and thin adapters on top.

```
┌──────────────────────────────────────────────────────────┐
│                    disvimat/core/                        │
│  document (tree) · elements · tables · keyboard          │
│  presentation · speech · calculator · integrity          │
│  filters/mathml · transcription/braille · ui_text        │
└───────────────┬──────────────────────┬───────────────────┘
                │                      │
   ┌────────────▼───────────┐ ┌────────▼──────────────────┐
   │ disvimat/desktop/      │ │ disvimat/web/             │
   │ wxPython, native       │ │ FastAPI + semantic HTML   │
   │ controls read by NVDA  │ │ with native MathML        │
   └────────────────────────┘ └───────────────────────────┘
```

`tests/test_architecture.py` enforces the rule in CI: importing the core
must never pull in `wx`, `fastapi` or any other interface library.

### Why two interfaces instead of one framework

Frameworks that promise "one code base, desktop and web" (Flet, Kivy…)
draw on a canvas and are **invisible to screen readers**. For this audience
that is disqualifying. So each interface uses what is most accessible on
its platform:

- **Desktop: wxPython.** Native Windows controls, exposed through MSAA/UIA,
  which NVDA reads with no extra work. NVDA's own interface is written in
  wxPython, which also matters for the future add-on (modules B3/E1).
- **Web: FastAPI + MathML.** MathML Core is rendered natively by Chrome,
  Firefox and Safari and spoken by screen readers, so the mathematics is
  real content rather than a picture.

The cost of two interfaces stays low because **the interfaces are thin**:
they translate events into canonical key strokes, hand them to the core,
and display the answer. All the behaviour is shared.

## The document

A document is a tree, not a string:

- `Character` — a plain text character (a digit, a letter).
- `Sign` — a catalogue sign, with no slots (`plus`, `equals`).
- `Structure` — a catalogue structure with slots (`fraction` has two).

The cursor is a path descending through structures plus an index in the
current sequence, and it always sits *between* two nodes. Because the
document is structural rather than textual, moving by structure, selecting
a numerator or transcribing to braille are natural operations instead of
string surgery.

Undo and redo work on snapshots of the whole document, but a snapshot
**does not copy the tree**: it holds references to the lines. A key stroke
only ever changes one line, so that line gets a private copy at the moment
it is edited and only then (copy-on-write); every other line is shared with
the history.

Copying the whole tree on every key stroke was simple and correct while a
document was a single expression; with multi-line documents it made the
cost of typing grow with the length of the document, and past a few hundred
nodes that is felt as lag while typing.

The rule the design rests on: **a line a snapshot still points at must
never be changed in place**. That is why the editing methods call
`_edit(...)` *before* taking any reference to a line, a slot or a matrix.
`tests/test_document.py` checks the invariant — no line marked private is
reachable from a snapshot — after every operation of a long, varied
session.

## The editing cycle

Every key stroke follows the same path in both interfaces:

1. The interface normalises the event to the **canonical form** of the
   tables: `"Left"`, `"Ctrl+F"`, `"+"`. These names are English and are
   never translated.
2. `Keyboard.resolve` maps the stroke to a catalogue element, honouring the
   user profile level (A7).
3. `Editor.press` applies it: a command runs, a sign or a structure is
   inserted.
4. The editor returns a `Result` with three things: the linear **text**,
   the caret **position** and the **speech** string.
5. The interface displays the text, places the caret and announces the
   speech — on the status line on the desktop, in an `aria-live` region on
   the web.

Because steps 2 to 4 are shared, the desktop and the web behave identically
by construction, not by discipline.

## Localisation

There is one single localisation mechanism: **JSON tables per language with
a fallback to English**. Speech (`labels`), program messages (`messages`)
and interface strings (`ui`) all work the same way, so a translator learns
one format and needs no build step.

Braille is the deliberate exception: `br6` tables **never fall back** to
another language. Mathematical braille is normative and differs by country
(CBE in Spain, UEB in English, NMB in French), so serving one country's
braille to another would be wrong. When a language has no braille table the
application disables its braille features instead of guessing.

## Module map

| Brief | Where it lives |
|---|---|
| A1 MathML filter | `core/filters/mathml.py` |
| A2–A4 keyboard tables | `core/keyboard.py` + `data/keys_*.json` |
| A7 profiles | `data/profiles.json`, applied in `core/keyboard.py` |
| A8–A9 calculator and lock | `core/calculator.py`, `core/editor.py` |
| B1 glyphs | `data/glyphs.json` + `core/presentation.py` |
| B2 speech | `data/labels.*.json` + `core/speech.py` |
| B4 presentation window | `desktop/app.py`, `web/static/` |
| B5–B6 braille and its window | `core/transcription/braille.py`, `desktop/app.py` |
| C1 XHTML export | `export/xhtml.py` |
| C3 BRA export | `core/transcription/braille.py` |
| D1 XHTML import | `core/filters/mathml.py` |
| E6 internationalisation | `core/ui_text.py` + the language tables |

For what is still missing, see [STATUS.md](STATUS.md).

## Maintenance rules

1. **The core imports nothing from the interfaces** (enforced by a test).
2. **Behaviour lives in data, not in code**: adding a sign, a key or a
   language means editing tables.
3. **The core holds no user-facing text.** If the program must say
   something new, it gets a message id and the text goes into a table.
4. **One table format, one set of integrity checks.** An inconsistent table
   breaks the build, never the user.
5. **Strict typing** (`mypy --strict`) and tests for every behaviour.
