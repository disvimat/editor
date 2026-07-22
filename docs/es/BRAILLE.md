# Braille — cómo se produce

**Idiomas:** [English](../en/BRAILLE.md) · [Español](../es/BRAILLE.md) · [Français](../fr/BRAILLE.md)

DISVIMAT no escribe tablas braille a mano. Usa los dos motores que usan las
tecnologías de asistencia como NVDA, cada uno para lo que mejor sabe, con
reserva escalonada:

```
braille matemático  →  MathCAT     (CMU, UEB, Nemeth…)   ┐
braille de texto    →  liblouis    (tablas oficiales)    ├─ escalera, en orden
último recurso      →  ntras tablas (br6.*.json)         ┘
```

## Por qué dos motores

- **[MathCAT](MATHCAT.md)** lee *notación* matemática (MathML) y produce
  braille matemático normativo: CMU para español, UEB para inglés. Es el
  braille correcto para las expresiones que edita el programa.
- **liblouis** traduce *texto* a braille con tablas oficiales y mantenidas
  para muchísimos idiomas. Es el traductor braille estándar detrás de NVDA,
  Orca y BrailleBlaster. Se ocupa de las partes de texto literario y da
  braille para idiomas que MathCAT no cubre (por ejemplo, el francés).

Son complementarios, no alternativas: NVDA usa los dos. Aquí MathCAT da el
braille de una expresión matemática completa; liblouis es la capa de
braille de texto por debajo; y nuestras tablas `br6` (cuyos valores
españoles son provisionales) son solo el último recurso cuando ningún
motor está instalado.

## La escalera en el código

`create_outputs` en [`backends.py`](../../src/disvimat/backends.py) elige el
motor de braille por idioma:

1. MathCAT si está instalado y cubre el idioma.
2. si no, liblouis si está instalado y tiene tabla de texto para el idioma.
3. si no, nuestras tablas `br6`.
4. si no, el braille se desactiva para ese idioma (nunca el de otro).

Cada capa es su propio adaptador tras el puerto `BrailleProvider`
([`core/output.py`](../../src/disvimat/core/output.py)):
[`core/mathcat.py`](../../src/disvimat/core/mathcat.py),
[`core/liblouis.py`](../../src/disvimat/core/liblouis.py),
[`core/transcription/braille.py`](../../src/disvimat/core/transcription/braille.py).

## Instalar liblouis

liblouis no es un simple `pip install`: es una biblioteca nativa más un
directorio de tablas. Para Windows de 64 bits hay un instalador de una
orden:

```bash
python scripts/install_liblouis.py
```

Descarga el `liblouis.dll` oficial y las tablas a
`site-packages/disvimat_liblouis/`, y verifica una traducción en español.
En Linux/macOS, instale liblouis con el gestor de paquetes
(`apt install liblouis`, `brew install liblouis`) y apunte `LIBLOUIS_DLL` y
`LOUIS_TABLEPATH` a la biblioteca y sus tablas.

Compruébelo:

```python
from disvimat.core.liblouis import is_available
print(is_available())          # True cuando se encuentran biblioteca y tablas
```

## Selección de tabla

La tabla de texto por idioma es un mapa pequeño y editable en
`core/liblouis.py` (`TEXT_TABLES`): español → `es-g1.ctb`, inglés →
`en-ueb-g1.ctb`, francés → `fr-bfu-comp6.utb`. El grado 1 (sin contracción)
es la opción segura junto a las matemáticas. Reorientar un idioma, o añadir
uno, es editar ese mapa — las tablas son de liblouis, no nuestras.

## Cosas que conviene saber

- **Verificado** en Python 3.13 de 64 bits (Windows): liblouis produce
  braille Unicode (modo `dotsIO | ucBrl`) con tablas oficiales: español
  `es-g1`, inglés `en-ueb-g1`, francés `fr-bfu-comp6`.
- **liblouis es un motor de texto.** Pasarle una expresión matemática
  completa daría braille de los símbolos de forma literal; por eso el
  braille matemático va por MathCAT. liblouis importa para las partes de
  texto, como reserva, y para idiomas de solo texto.
- **Determinismo en los tests.** `DISVIMAT_NO_LIBLOUIS=1` (y
  `DISVIMAT_NO_MATHCAT=1`) fuerzan nuestras tablas aunque los motores estén
  instalados; la batería fija ambos para que los resultados sean idénticos
  con o sin las bibliotecas nativas.
