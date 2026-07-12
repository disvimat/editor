# Tablas DisvimatEditor

Aquí viven **todas** las tablas de correspondencia del editor, en el
formato único acordado (decisión previa "b" del [README](../README.md)).
Añadir un signo, cambiar una pulsación o traducir una etiqueta es editar
estos archivos: no hay que tocar código Python.

## Envoltura común

```json
{
  "tabla": "nombre_de_la_tabla",
  "version": 1,
  "lengua": "es",
  "entradas": [ ... ]
}
```

- `lengua` es `null` en las tablas independientes de la lengua; las
  dependientes llevan además sufijo en el nombre: `etiquetas.es.json`.
- Los `id` de las entradas referencian siempre el catálogo
  `elementos.json` y siguen el patrón `[a-z][a-z0-9_]*`.

## Tablas actuales

| Archivo | Módulo README | Contenido |
|---------|---------------|-----------|
| `elementos.json` | — (decisión "a") | catálogo: id, tipo, categoría, MathML/Unicode, aridad, nivel |
| `teclas_signos.json` | A2 | signo/estructura → pulsación |
| `teclas_comandos.json` | A3 | comando → pulsación |
| `teclas_numpad.json` | A4 | pulsaciones alternativas en el bloque numérico |
| `perfiles.json` | A7 | perfiles de usuario → nivel máximo de elementos |
| `glifos.json` | B1 | signo/estructura → glifo de presentación lineal (con `plantilla` en estructuras) |
| `etiquetas.es.json` | B2 | elemento → etiqueta hablada (con `partes` inicio/separador/fin en estructuras) |
| `br6.es.json` | B5 | elemento → celdas braille de 6 puntos (con `partes` en estructuras) |
| `br6_texto.es.json` | B5 | letra/dígito → celdas braille de 6 puntos |

**Aviso braille**: los valores de `br6.es.json` son provisionales y
deben revisarse contra la signografía matemática de la CBE (Comisión
Braille Española) antes de darlos por buenos; corregirlos es editar el
JSON, sin tocar código. La exportación .BRA usa de momento la
codificación ASCII NABCC (constante en
`src/disvimat/core/transcripcion/braille.py`).

## Convenciones

- **Pulsaciones** (`teclas`): nombres canónicos en inglés, que es lo que
  emiten wx y el navegador: `"+"`, `"Left"`, `"Ctrl+F"`, `"Ctrl+Shift+R"`.
- **Condicionantes** (`condicion`, opcional): expresión que restringe
  cuándo aplica la entrada (README A3); se definirá su gramática en la
  Fase 1.

## Integridad

`tests/test_integridad.py` comprueba en cada build que:

1. toda entrada referencia un `id` existente en `elementos.json`;
2. todo signo/estructura tiene glifo y todo elemento tiene etiqueta;
3. ninguna pulsación está asignada dos veces (ni entre signos y comandos).

Una tabla incoherente rompe la CI, no al usuario.
