# Add-ons — ampliar el editor sin tocar el núcleo (módulo A5)

**Idiomas:** [English](../en/ADDONS.md) · [Español](../es/ADDONS.md) · [Français](../fr/ADDONS.md)

Un add-on es Python corriente que **registra lo que aporta**. El editor lo
integra como si fuera de serie: misma resolución de teclas, misma voz,
mismo deshacer. No hay que modificar el editor para añadir funciones.

## El add-on más pequeño

```python
def register(registry):
    registry.add_command(
        id="contar",
        run=lambda editor: f"{len(editor.document.current_line())} elementos",
        keys="Ctrl+Alt+C",
        labels={"es": "contar la línea", "en": "count the line"},
    )
```

Eso es todo. Al arrancar, el editor:

1. añade `contar` al **catálogo** como comando,
2. le asigna la **tecla** `Ctrl+Alt+C`,
3. registra su **etiqueta hablada** en cada idioma,
4. y lo pone en la tabla de despacho, junto a los comandos internos.

## Cómo se descubren

**Carpeta de scripts** — lo más rápido para un profesor o un usuario:

```
set DISVIMAT_ADDONS=C:\Users\yo\disvimat-addons
```

Cada `.py` de esa carpeta con una función `register(registry)` se carga al
arrancar. Es el "diseñador de scripts" que pedía el documento original.

**Paquete instalable** — la forma normal de distribuir uno. En su
`pyproject.toml`:

```toml
[project.entry-points."disvimat.addons"]
mi-addon = "mi_addon:register"
```

## Lo que puede aportar

| Llamada | Aporta |
|---|---|
| `registry.add_command(id, run, keys=…, labels=…)` | un comando con tecla y voz |
| `registry.add_exporter(id, extension, dump, labels=…)` | un formato de exportación |

La función `run(editor)` recibe el editor: puede leer y modificar el
documento (`editor.document`), insertar contenido (`editor.type_character`)
y devuelve **el texto que se hablará**.

## Un fallo nunca tumba el editor

- Un add-on que revienta **al cargarse** se anota en `registry.errors` y los
  demás siguen cargándose.
- Un comando que lanza una excepción **al ejecutarse** se contiene: el
  usuario oye "el complemento no pudo ejecutarse" (traducible, está en la
  tabla `messages`) y el editor sigue funcionando.

Está cubierto por tests: `tests/test_addons.py`.

## Ejemplo completo

En [`examples/addons/count_elements.py`](../../examples/addons/count_elements.py)
hay un add-on real y funcionando que cuenta los elementos de la línea
actual, con etiquetas en español, inglés y francés.

## Desactivarlos

`create_editor(addons=False)` construye un editor sin ningún add-on, que es
lo que hace la batería de tests para ser determinista.
