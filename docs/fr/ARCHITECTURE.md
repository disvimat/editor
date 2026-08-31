# Architecture

**Langues :** [English](../en/ARCHITECTURE.md) · [Español](../es/ARCHITECTURE.md) · [Français](../fr/ARCHITECTURE.md)

## L'idée à retenir

Presque tout le comportement de l'éditeur relève des **données, pas du
code**. Quelle touche insère quel signe, comment une fraction est dessinée,
oralisée, transcrite en braille : tout cela vit dans des tables JSON sous
`data/`. Ajouter un signe, changer un raccourci ou traduire l'éditeur dans
une autre langue, c'est modifier une table, pas écrire du Python.

C'était la demande du document initial — « un seul format de tables, un
seul éditeur de tables » — et c'est la colonne vertébrale de la conception.

## Couches

Le projet suit une architecture hexagonale (ports et adaptateurs) : un
noyau en Python pur qui ignore tout des interfaces, et des adaptateurs
minces par-dessus.

```
┌──────────────────────────────────────────────────────────┐
│                    disvimat/core/                        │
│  document (arbre) · elements · tables · keyboard         │
│  presentation · speech · calculator · integrity          │
│  filters/mathml · transcription/braille · ui_text        │
└───────────────┬──────────────────────┬───────────────────┘
                │                      │
   ┌────────────▼───────────┐ ┌────────▼──────────────────┐
   │ disvimat/desktop/      │ │ disvimat/web/             │
   │ wxPython, contrôles    │ │ FastAPI + HTML sémantique │
   │ natifs lus par NVDA    │ │ avec MathML natif         │
   └────────────────────────┘ └───────────────────────────┘
```

`tests/test_architecture.py` fait respecter la règle dans l'intégration
continue : importer le noyau ne doit jamais entraîner `wx`, `fastapi` ni
aucune autre bibliothèque d'interface.

### Pourquoi deux interfaces plutôt qu'un framework unique

Les frameworks qui promettent « un seul code, bureau et web » (Flet,
Kivy…) dessinent sur un canevas et sont **invisibles pour les lecteurs
d'écran**. Pour ce public, c'est rédhibitoire. Chaque interface emploie
donc ce qui est le plus accessible sur sa plateforme :

- **Bureau : wxPython.** Des contrôles Windows natifs, exposés par
  MSAA/UIA, que NVDA lit sans travail supplémentaire. L'interface de NVDA
  est elle-même écrite en wxPython, ce qui compte aussi pour le futur
  module complémentaire (modules B3/E1).
- **Web : FastAPI + MathML.** MathML Core est rendu nativement par Chrome,
  Firefox et Safari, et oralisé par les lecteurs d'écran : les
  mathématiques sont un contenu réel, pas une image.

Le coût de deux interfaces reste faible parce que **les interfaces sont
minces** : elles traduisent les événements en frappes canoniques, les
transmettent au noyau et affichent la réponse. Tout le comportement est
partagé.

## Le document

Un document est un arbre, pas une chaîne :

- `Character` — un caractère de texte brut (un chiffre, une lettre).
- `Sign` — un signe du catalogue, sans case (`plus`, `equals`).
- `Structure` — une structure du catalogue avec des cases (`fraction` en a deux).

Le curseur est un chemin qui descend à travers les structures, plus un
indice dans la séquence courante ; il se trouve toujours *entre* deux
nœuds. Le document étant structurel et non textuel, se déplacer par
structure, sélectionner un numérateur ou transcrire en braille sont des
opérations naturelles, et non de la chirurgie de chaînes.

Annuler et rétablir travaillent sur des instantanés du document entier,
mais un instantané **ne copie pas l'arbre** : il garde des références aux
lignes. Une frappe ne change qu'une ligne, donc celle-ci reçoit une copie
privée au moment où elle est modifiée, et seulement alors
(*copy-on-write*) ; les autres lignes sont partagées avec l'historique.

Copier l'arbre entier à chaque frappe était simple et correct tant qu'un
document tenait en une expression ; avec des documents multilignes, le coût
de la saisie croissait avec la longueur du document, ce qui, au-delà de
quelques centaines de nœuds, se ressent comme une latence à la frappe.

La règle qui fonde le dessin : **une ligne qu'un instantané référence
encore ne doit jamais être modifiée sur place**. C'est pourquoi les
méthodes d'édition appellent `_edit(...)` *avant* de prendre la moindre
référence à une ligne, à un emplacement ou à une matrice.
`tests/test_document.py` vérifie l'invariant — aucune ligne marquée privée
n'est atteignable depuis un instantané — après chaque opération d'une
session longue et variée.

## Le cycle d'édition

Chaque frappe suit le même chemin dans les deux interfaces :

1. L'interface normalise l'événement vers la **forme canonique** des
   tables : `"Left"`, `"Ctrl+F"`, `"+"`. Ces noms sont en anglais et ne
   sont jamais traduits. Ce que chaque plateforme envoie pour chaque nom
   vit dans `data/keys_platform.json`, que lisent les deux adaptateurs :
   c'est ce qui les empêche de diverger sur une même touche physique.
2. `Keyboard.resolve` la convertit en élément du catalogue, en respectant
   le niveau du profil d'utilisateur (A7).
3. `Editor.press` l'applique : une commande s'exécute, ou un signe ou une
   structure est inséré.
4. L'éditeur renvoie un `Result` avec trois éléments : le **texte**
   linéaire, la **position** du curseur et la chaîne de **voix**.
5. L'interface affiche le texte, place le curseur et annonce la voix : dans
   la barre d'état sur le bureau, dans une région `aria-live` sur le web.

Les étapes 2 à 4 étant partagées, le bureau et le web se comportent de
façon identique par construction, et non par discipline.

## Localisation

Il n'existe qu'un seul mécanisme de localisation : des **tables JSON par
langue, avec repli sur l'anglais**. La voix (`labels`), les messages du
programme (`messages`) et les chaînes d'interface (`ui`) fonctionnent de la
même manière : un traducteur n'apprend qu'un format et n'a besoin d'aucune
étape de compilation.

Le braille est l'exception délibérée : les tables `br6` **ne se replient
jamais** sur une autre langue. Le braille mathématique est normatif et
diffère selon les pays (CBE en Espagne, UEB en anglais, NMB en français) ;
servir le braille d'un pays à un autre serait donc erroné. Lorsqu'une
langue n'a pas de table braille, l'application désactive ses fonctions
braille au lieu de deviner.

## Carte des modules

| Document initial | Emplacement |
|---|---|
| A1 filtre MathML | `core/filters/mathml.py` |
| A2–A4 tables de clavier | `core/keyboard.py` + `data/keys_*.json` |
| A7 profils | `data/profiles.json`, appliqué dans `core/keyboard.py` |
| A8–A9 calculatrice et verrou | `core/calculator.py`, `core/editor.py` |
| B1 glyphes | `data/glyphs.json` + `core/presentation.py` |
| B2 oralisation | `data/labels.*.json` + `core/speech.py` |
| B4 fenêtre de présentation | `desktop/app.py`, `web/static/` |
| B5–B6 braille et sa fenêtre | `core/transcription/braille.py`, `desktop/app.py` |
| C1 export XHTML | `export/xhtml.py` |
| C3 export BRA | `core/transcription/braille.py` |
| D1 import XHTML | `core/filters/mathml.py` |
| E6 internationalisation | `core/ui_text.py` + les tables par langue |

Ce qui manque encore figure dans [STATUS.md](STATUS.md).

## Règles de maintenance

1. **Le noyau n'importe rien des interfaces** (vérifié par un test).
2. **Le comportement vit dans les données, pas dans le code** : ajouter un
   signe, une touche ou une langue, c'est modifier des tables.
3. **Le noyau ne contient aucun texte destiné à l'utilisateur.** Si le
   programme doit dire quelque chose de nouveau, il reçoit un identifiant
   de message et le texte va dans une table.
4. **Un format de table, un jeu de contrôles d'intégrité.** Une table
   incohérente casse la construction, jamais l'utilisateur.
5. **Typage strict** (`mypy --strict`) et tests pour chaque comportement.
