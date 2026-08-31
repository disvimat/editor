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

## Cómo instalarlo

MathCAT **no está en PyPI**, pero el proyecto publica binarios
precompilados (con PyO3 abi3, así que una compilación sirve para cualquier
Python 3.x). Para Python de 64 bits en Windows o Linux hay un instalador de
una sola orden:

```bash
python scripts/install_mathcat.py
```

Descarga el binario `libmathcat_py` que corresponde y el directorio
`Rules` de MathCAT a `site-packages`, y verifica la instalación. Después,
el editor usa MathCAT automáticamente, sin tocar código ni configuración.

Compruébelo a mano con:

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True cuando el enlace y las reglas están

from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

Para una plataforma sin binario precompilado (por ejemplo 32 bits, o un
Python que el release no cubra), compílelo desde el código: instale el
[toolchain de Rust](https://rustup.rs/), clone
[daisy/MathCATForPython](https://github.com/daisy/MathCATForPython) y
compílelo (proyecto PyO3); luego deje `libmathcat_py` y un directorio
`Rules` en la ruta de Python.

## Cómo está cableado

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — el adaptador.
  `SetRulesDir` se llama **primero** (MathCAT lo exige antes de cualquier
  preferencia), y luego `Language`, `SpeechStyle` y `BrailleCode`; localiza
  las reglas con la variable `MATHCAT_RULES_DIR` o una carpeta `Rules`
  junto al enlace.
- [`backends.py`](../../src/disvimat/backends.py) — la política: MathCAT
  manda, las tablas son la reserva. Con `DISVIMAT_NO_MATHCAT=1` se fuerzan
  las tablas aunque MathCAT esté instalado (la batería de tests lo hace,
  para que los resultados no dependan de si MathCAT está presente).
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — ejercita el
  adaptador con una biblioteca falsa, cubriendo la frontera sin necesitar
  el enlace real.

## Cosas que conviene saber

- **Verificado y funcionando** en Python 3.13 de 64 bits (Windows): el
  español lee "1 más 2 tercios" y produce braille CMU; el inglés usa UEB.
  Cuando MathCAT no está, el editor funciona sobre nuestras tablas igual
  que antes.
- **Francés.** MathCAT trae *reglas* de francés, pero incompletas (recurren
  al inglés en muchas expresiones), así que de momento mantenemos el
  francés en nuestras tablas. Cuando esas reglas maduren, añadir `"fr"` a
  `SPEECH_LANGUAGES` es el único cambio necesario.
- **Singleton global — resuelto.** El enlace de MathCAT guarda una única
  configuración por proceso. En escritorio da igual (un idioma por
  ejecución), pero en web cada sesión construye su propio backend sobre esa
  única biblioteca, y no era una interferencia hipotética: la última sesión
  creada le quitaba el idioma a todas las demás. Verificado con MathCAT
  real, un lector español recibía «1 and 1 half» y braille **UEB** en lugar
  de CMU en cuanto alguien abría una sesión en inglés — braille incorrecto
  presentado como correcto, justo lo que la política de abajo prohíbe.
  Ahora ningún backend guarda estado dentro de la biblioteca: cada llamada
  vuelve a fijar sus preferencias y lee la respuesta sin soltar un cerrojo
  de módulo. Reaplicarlas cuesta 0,0012 ms frente a 0,22 ms de la lectura.

## Política braille

Cuando MathCAT esté disponible, su braille manda en español, y nuestras
tablas `br6` quedan como reserva para cuando no esté instalado y para los
idiomas que él no cubra. El braille nunca recurre a otro idioma: un idioma
sin fuente braille simplemente tiene desactivadas sus funciones braille.
