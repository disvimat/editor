# Integración de MathCAT

**Idiomas:** [English](../en/MATHCAT.md) · [Español](../es/MATHCAT.md) · [Français](../fr/MATHCAT.md)

[MathCAT](https://daisy.github.io/MathCAT/) (DAISY, licencia MIT) convierte
MathML en voz y braille. Adoptarlo importa a este proyecto sobre todo por
una razón: **implementa CMU**, el *Código Matemático Unificado*, la
signografía matemática braille española, mantenida por especialistas, al
contrario que nuestras tablas, que son explícitamente provisionales.

## Por qué encaja

Nuestro núcleo ya produce MathML (módulo C1), y MathML es justamente lo que
MathCAT consume. Así que MathCAT entra por los dos puertos de salida
definidos en [`core/output.py`](../../src/disvimat/core/output.py) sin que
el documento, el teclado ni la calculadora sepan nada de él.

| | Origen |
|---|---|
| Lectura de la expresión completa | MathCAT si está disponible; nuestras tablas `labels` si no |
| Braille (pantalla, línea, `.BRA`) | MathCAT si está disponible; nuestras tablas `br6` si no |
| **Voz de edición** ("hueco 2", "salir de la estructura: fracción") | **siempre nuestras tablas** |

Esa última fila es la distinción importante: MathCAT lee *notación*
matemática; no narra una sesión de edición. Hacen falta las dos voces y
vienen de sitios distintos.

## Qué cubre MathCAT y qué no

- **Códigos braille:** Nemeth, UEB Technical, **CMU**, vietnamita, LaTeX
  alemán/austriaco, ASCIIMath.
- **Voz:** inglés, alemán, español, finés, indonesio, noruego, sueco,
  vietnamita, chino tradicional. **No hay francés**, así que el francés
  sigue usando íntegramente nuestras tablas.
- **Navegación:** MathCAT navega una expresión *estática*; nuestro editor
  necesita un cursor que inserta y borra. Son modelos distintos, así que su
  navegación no se usa para editar.

## Estado actual

La **costura está implementada y probada**; el **binario todavía no está
compilado**.

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — el adaptador:
  fija `Language`, `SpeechStyle` y `BrailleCode`, entrega nuestro MathML y
  devuelve voz y braille.
- [`backends.py`](../../src/disvimat/backends.py) — la política: MathCAT
  manda, las tablas son la reserva.
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — ejercita el
  adaptador con una biblioteca falsa, de modo que todo lo que está de
  nuestro lado de la frontera queda verificado.

Como MathCAT hoy no está, la aplicación funciona igual que antes sobre
nuestras tablas. Basta con instalar el binario para que cambie de motor:
no hay que tocar código.

## Compilar el enlace Python

MathCAT **no está publicado en PyPI**, y el binario que acompaña al add-on
de NVDA está compilado para Python 3.11 de 32 bits (el intérprete de NVDA),
así que no puede importarse desde un Python normal de 64 bits. Hay que
compilarlo:

1. Instalar el [toolchain de Rust](https://rustup.rs/).
2. Clonar [daisy/MathCATForPython](https://github.com/daisy/MathCATForPython)
   y compilarlo para su versión y arquitectura de Python (es un proyecto
   PyO3; siga las instrucciones de compilación de ese repositorio).
3. Dejar el módulo resultante (`libmathcat_py`) en la ruta de Python del
   entorno donde corre DISVIMAT.
4. Poner a disposición el directorio **Rules**. MathCAT lo busca en la ruta
   dada a `SetRulesDir`, luego en la variable de entorno
   `MathCATRulesDir`, y por último junto al binario. Nuestro adaptador
   acepta un argumento `rules_dir` para la primera opción.

Compruébelo con:

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True cuando el enlace se puede importar
```

y después:

```python
from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

Dos detalles que conviene confirmar sobre una compilación real, porque no
se pudieron probar sin la biblioteca: el nombre exacto del módulo
(probamos `libmathcat_py` y luego `libmathcat`) y las cadenas de los
códigos braille (`"CMU"`, `"UEB"`). Ambos son constantes al principio de
`core/mathcat.py`.

## Política braille

Cuando MathCAT esté disponible, su braille manda en español, y nuestras
tablas `br6` quedan como reserva para cuando no esté instalado y para los
idiomas que él no cubra. El braille nunca recurre a otro idioma: un idioma
sin fuente braille simplemente tiene desactivadas sus funciones braille.
