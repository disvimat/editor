# El documento — multilínea y el formato `.dvm`

**Idiomas:** [English](../en/DOCUMENT.md) · [Español](../es/DOCUMENT.md) · [Français](../fr/DOCUMENT.md)

## Documentos multilínea

Un documento es una lista de **líneas**; cada línea es un árbol de expresión
(la misma estructura de antes). El cursor lleva un número de línea además de
su camino e índice.

- `Intro` crea una línea nueva, partiendo la actual por el cursor.
- En el nivel superior (fuera de una estructura) las flechas `Arriba`/`Abajo`
  se mueven a la línea anterior/siguiente; dentro de una estructura siguen
  saliendo/entrando de ella.
- `Retroceso` al inicio de una línea la fusiona con la anterior; `Supr` al
  final fusiona la siguiente.
- Cada línea se presenta, se lee y se transcribe a braille por separado; la
  línea de estado lee la línea **actual**, y `Calcular` la calcula.

## El formato `.dvm`

`.dvm` (documento DisViMat) es el formato de guardado propio del proyecto. A
diferencia de la exportación XHTML —un formato de presentación—, guarda el
árbol **exactamente**, así que guardar y reabrir es una ida y vuelta sin
pérdida. Es JSON: inspeccionable y con diffs limpios en git.

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

- `language` y `profile` registran con qué se escribió el documento, para
  restaurar la voz, el braille y el nivel adecuados.
- Cada nodo es uno de `{"char": …}`, `{"sign": <id>}` o
  `{"structure": <id>, "slots": [...]}`; los ids son los del catálogo, los
  mismos identificadores estables que usa todo lo demás.
- `version` protege la compatibilidad: una versión desconocida se rechaza
  con un error claro en vez de leerse mal.

## Cómo usarlo

**Escritorio** — menú Archivo: Nuevo, Abrir (`Ctrl+O`), Guardar (`Ctrl+S`);
el diálogo filtra `*.dvm`. Importar/Exportar XHTML y Exportar braille siguen
en el mismo menú.

**Web** — los botones *Abrir (.dvm)* y *Guardar (.dvm)*; guardar descarga el
`.dvm`, abrir lee un archivo elegido de vuelta en la sesión.

## En el código

[`core/dvm.py`](../../src/disvimat/core/dvm.py) tiene `to_dvm(lines,
language=…, profile=…)` y `from_dvm(text) -> DvmDocument`. El modelo de
documento vive en [`core/document.py`](../../src/disvimat/core/document.py);
`Document.lines` es la lista de líneas, y `Editor.load_lines(lines)`
sustituye el contenido (deshacible). La ida y vuelta y las operaciones de
línea están cubiertas por `tests/test_dvm.py` y `tests/test_multiline.py`.
