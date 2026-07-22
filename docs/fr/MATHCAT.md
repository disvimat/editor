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

## Comment l'installer

MathCAT **n'est pas sur PyPI**, mais le projet publie des binaires
précompilés (avec PyO3 abi3, si bien qu'une compilation sert à tout Python
3.x). Pour un Python 64 bits sous Windows ou Linux, un installateur en une
commande existe :

```bash
python scripts/install_mathcat.py
```

Il télécharge le binaire `libmathcat_py` correspondant et le répertoire
`Rules` de MathCAT dans `site-packages`, puis vérifie l'installation.
Ensuite, l'éditeur utilise MathCAT automatiquement, sans modification de
code ni de configuration.

Vérifiez à la main avec :

```python
from disvimat.core.mathcat import is_available
print(is_available())          # True dès que l'interface et les règles sont là

from disvimat.core.tables import Catalog, data_dir
from disvimat.backends import create_outputs
outputs = create_outputs(Catalog.load(data_dir() / "elements.json"), "es")
print(outputs.speech_backend, outputs.braille_backend)   # -> mathcat mathcat
```

Pour une plateforme sans binaire précompilé (par exemple 32 bits, ou un
Python que la version ne couvre pas), compilez depuis les sources :
installez la [chaîne d'outils Rust](https://rustup.rs/), clonez
[daisy/MathCATForPython](https://github.com/daisy/MathCATForPython) et
compilez-le (projet PyO3), puis placez `libmathcat_py` et un répertoire
`Rules` sur le chemin Python.

## Comment c'est branché

- [`core/mathcat.py`](../../src/disvimat/core/mathcat.py) — l'adaptateur.
  `SetRulesDir` est appelé **en premier** (MathCAT l'exige avant toute
  préférence), puis `Language`, `SpeechStyle` et `BrailleCode` ; il localise
  les règles via la variable `MATHCAT_RULES_DIR` ou un dossier `Rules` à
  côté de l'interface.
- [`backends.py`](../../src/disvimat/backends.py) — la politique : MathCAT
  d'abord, les tables en secours. `DISVIMAT_NO_MATHCAT=1` force les tables
  même si MathCAT est installé (la suite de tests le fait, pour que les
  résultats ne dépendent pas de la présence de MathCAT).
- [`tests/test_mathcat.py`](../../tests/test_mathcat.py) — pilote
  l'adaptateur avec une bibliothèque factice, couvrant la frontière sans
  l'interface réelle.

## Bon à savoir

- **Vérifié et fonctionnel** sous Python 3.13 64 bits (Windows) :
  l'espagnol lit « 1 más 2 tercios » et produit du braille CMU ; l'anglais
  utilise l'UEB. En l'absence de MathCAT, l'éditeur tourne sur nos tables
  comme avant.
- **Français.** MathCAT fournit des *règles* françaises, mais incomplètes
  (elles se replient sur l'anglais pour de nombreuses expressions) ; nous
  gardons donc le français sur nos tables pour l'instant. Quand ces règles
  auront mûri, ajouter `"fr"` à `SPEECH_LANGUAGES` sera le seul changement
  nécessaire.
- **Singleton global.** L'interface MathCAT ne détient qu'une configuration
  globale par processus. C'est adapté au bureau (une langue par exécution).
  Sur le web, des sessions concurrentes dans des langues *différentes*
  pourraient interférer ; un déploiement monolingue l'évite. Un verrou par
  processus ou une affinité de worker est la solution si l'usage web
  multilingue devient important.

## Politique braille

Une fois MathCAT disponible, son braille l'emporte pour l'espagnol, et nos
tables `br6` restent en secours lorsqu'il n'est pas installé et pour les
langues qu'il ne couvre pas. Le braille ne se replie jamais sur une autre
langue : une langue sans source braille voit simplement ses fonctions
braille désactivées.
