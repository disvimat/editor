# Intégration de MathCAT

**Langues :** [English](../en/MATHCAT.md) · [Español](../es/MATHCAT.md) · [Français](../fr/MATHCAT.md)

[MathCAT](https://daisy.github.io/MathCAT/) (DAISY, licence MIT) convertit
le MathML en parole et en braille. Son adoption compte pour ce projet avant
tout pour une raison : **il implémente CMU**, le *Código Matemático
Unificado*, la notation mathématique braille espagnole, maintenue par des
spécialistes — contrairement à nos propres tables, explicitement
provisoires.

## Pourquoi cela s'emboîte

Notre noyau produit déjà du MathML (module C1), et le MathML est
précisément ce que MathCAT consomme. MathCAT se branche donc sur les deux
ports de sortie définis dans
[`core/output.py`](../../src/disvimat/core/output.py) sans que le document,
le clavier ou la calculatrice en sachent quoi que ce soit.

| | Source |
|---|---|
| Lecture de l'expression entière | MathCAT s'il est disponible ; nos tables `labels` sinon |
| Braille (écran, afficheur, `.BRA`) | MathCAT s'il est disponible ; nos tables `br6` sinon |
| **Voix d'édition** (« case 2 », « sortir de la structure : fraction ») | **toujours nos tables** |

Cette dernière ligne est la distinction essentielle : MathCAT lit la
*notation* mathématique ; il ne raconte pas une séance d'édition. Les deux
voix sont nécessaires et proviennent d'endroits différents.

## Ce que MathCAT couvre et ne couvre pas

- **Codes braille :** Nemeth, UEB Technical, **CMU**, vietnamien, LaTeX
  allemand/autrichien, ASCIIMath.
- **Parole :** anglais, allemand, espagnol, finnois, indonésien, norvégien,
  suédois, vietnamien, chinois traditionnel. **Le français est absent** :
  il continue donc d'utiliser entièrement nos tables.
- **Navigation :** MathCAT parcourt une expression *statique* ; notre
  éditeur a besoin d'un curseur qui insère et supprime. Les deux modèles
  diffèrent, sa navigation n'est donc pas utilisée pour l'édition.

## État actuel

La **couture est implémentée et testée** ; le **binaire n'est pas encore
compilé**.

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — l'adaptateur :
  il fixe `Language`, `SpeechStyle` et `BrailleCode`, transmet notre MathML
  et renvoie parole et braille.
- [`backends.py`](../../src/disvimat/backends.py) — la politique : MathCAT
  d'abord, les tables en secours.
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — pilote
  l'adaptateur avec une bibliothèque factice, ce qui vérifie tout ce qui se
  trouve de notre côté de la frontière.

MathCAT étant absent aujourd'hui, l'application fonctionne comme avant sur
nos tables. Installer le binaire suffit à basculer : aucun changement de
code n'est nécessaire.

## Compiler l'interface Python

MathCAT **n'est pas publié sur PyPI**, et le binaire livré avec le module
complémentaire NVDA est compilé pour Python 3.11 en 32 bits (l'interpréteur
de NVDA) ; il ne peut donc pas être importé par un Python 64 bits
ordinaire. Il faut le compiler :

1. Installer la [chaîne d'outils Rust](https://rustup.rs/).
2. Cloner [daisy/MathCATForPython](https://github.com/daisy/MathCATForPython)
   et le compiler pour votre version et votre architecture de Python (c'est
   un projet PyO3 ; suivez les instructions de compilation de ce dépôt).
3. Placer le module obtenu (`libmathcat_py`) sur le chemin Python de
   l'environnement qui exécute DISVIMAT.
4. Rendre disponible le répertoire **Rules**. MathCAT le cherche dans le
   chemin passé à `SetRulesDir`, puis dans la variable d'environnement
   `MathCATRulesDir`, puis à côté du binaire. Notre adaptateur accepte un
   argument `rules_dir` pour la première option.

Vérifiez avec :

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True dès que l'interface est importable
```

puis :

```python
from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

Deux détails à confirmer sur une compilation réelle, faute d'avoir pu les
tester sans la bibliothèque : le nom exact du module (nous essayons
`libmathcat_py` puis `libmathcat`) et les chaînes des codes braille
(`"CMU"`, `"UEB"`). Ce sont deux constantes en tête de `core/mathcat.py`.

## Politique braille

Une fois MathCAT disponible, son braille l'emporte pour l'espagnol, et nos
tables `br6` restent en secours lorsqu'il n'est pas installé et pour les
langues qu'il ne couvre pas. Le braille ne se replie jamais sur une autre
langue : une langue sans source braille voit simplement ses fonctions
braille désactivées.
