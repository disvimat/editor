# Add-ons — extending the editor without touching the core (module A5)

**Languages:** [English](../en/ADDONS.md) · [Español](../es/ADDONS.md) · [Français](../fr/ADDONS.md)

An add-on is ordinary Python that **registers what it contributes**. The
editor wires it in as if it were built in: same key resolution, same
speech, same undo. Adding a feature never means editing the editor.

## The smallest add-on

```python
def register(registry):
    registry.add_command(
        id="count",
        run=lambda editor: f"{len(editor.document.current_line())} elements",
        keys="Ctrl+Alt+C",
        labels={"en": "count the line", "es": "contar la línea"},
    )
```

That is all. At start-up the editor:

1. adds `count` to the **catalogue** as a command,
2. binds the **key stroke** `Ctrl+Alt+C`,
3. registers its **spoken label** per language,
4. and puts it in the dispatch table beside the built-in commands.

## How they are found

**A folder of scripts** — the quick path for a teacher or a user:

```
set DISVIMAT_ADDONS=C:\Users\me\disvimat-addons
```

Every `.py` in that folder with a `register(registry)` function is loaded
at start-up. This is the "script designer" the original brief asked for.

**An installed package** — the normal way to distribute one. In its
`pyproject.toml`:

```toml
[project.entry-points."disvimat.addons"]
my-addon = "my_addon:register"
```

## What it can contribute

| Call | Contributes |
|---|---|
| `registry.add_command(id, run, keys=…, labels=…)` | a command with a key and speech |
| `registry.add_exporter(id, extension, dump, labels=…)` | an export format |

`run(editor)` receives the editor: it can read and change the document
(`editor.document`), insert content (`editor.type_character`), and returns
**the text to speak**.

## A failure never takes the editor down

- An add-on that breaks **while loading** is recorded in `registry.errors`
  and the others still load.
- A command that raises **while running** is contained: the user hears
  "the add-on could not run" (translatable — it lives in the `messages`
  table) and the editor keeps working.

Both are covered by `tests/test_addons.py`.

## A full example

[`examples/addons/count_elements.py`](../../examples/addons/count_elements.py)
is a real, working add-on that counts the elements on the current line,
with labels in English, Spanish and French.

## Turning them off

`create_editor(addons=False)` builds an editor with no add-ons at all,
which is what the test suite does to stay deterministic.
