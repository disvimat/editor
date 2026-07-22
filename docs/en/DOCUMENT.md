# The document — multi-line and the `.dvm` format

**Languages:** [English](../en/DOCUMENT.md) · [Español](../es/DOCUMENT.md) · [Français](../fr/DOCUMENT.md)

## Multi-line documents

A document is a list of **lines**; each line is one expression tree (the
same structure as before). The cursor carries a line number in addition to
its path and index.

- `Return` starts a new line, splitting the current one at the cursor.
- At the top level (not inside a structure) the `Up`/`Down` arrows move to
  the previous/next line; inside a structure they still exit/enter it.
- `Backspace` at the start of a line merges it into the previous one;
  `Delete` at the end merges the next one in.
- Each line renders, speaks and transcribes to braille on its own; the
  status line reads the **current** line, and `Calculate` computes it.

## The `.dvm` format

`.dvm` (DisViMat document) is the project's own save format. Unlike the
XHTML export — a presentation format — it stores the tree **exactly**, so
saving and reopening round-trips with no loss. It is JSON, so it is
inspectable and diffs cleanly in git.

```json
{
  "format": "disvimat-document",
  "version": 1,
  "language": "es",
  "profile": "beginner",
  "lines": [
    [ {"char": "1"}, {"sign": "plus"}, {"char": "2"} ],
    [ {"structure": "fraction", "slots": [ [{"char": "3"}], [{"char": "4"}] ]} ]
  ]
}
```

- `language` and `profile` record what the document was written with, so a
  reader can restore the right speech, braille and level.
- Each node is one of `{"char": …}`, `{"sign": <id>}` or
  `{"structure": <id>, "slots": [...]}`; ids are the catalogue ids, the
  same stable identifiers everything else uses.
- `version` guards forward compatibility: an unknown version is refused
  with a clear error rather than misread.

## Using it

**Desktop** — File menu: New, Open (`Ctrl+O`), Save (`Ctrl+S`); the file
dialog filters `*.dvm`. Import/Export XHTML and Export braille stay in the
same menu.

**Web** — the *Open (.dvm)* and *Save (.dvm)* buttons; save downloads the
`.dvm`, open reads a chosen file back into the session.

## In code

[`core/dvm.py`](../../src/disvimat/core/dvm.py) has `to_dvm(lines,
language=…, profile=…)` and `from_dvm(text) -> DvmDocument`. The document
model lives in [`core/document.py`](../../src/disvimat/core/document.py);
`Document.lines` is the list of lines, and `Editor.load_lines(lines)`
replaces the content (undoable). Round trip and the line operations are
covered by `tests/test_dvm.py` and `tests/test_multiline.py`.
