# Le document — multi-lignes et le format `.dvm`

**Langues :** [English](../en/DOCUMENT.md) · [Español](../es/DOCUMENT.md) · [Français](../fr/DOCUMENT.md)

## Documents multi-lignes

Un document est une liste de **lignes** ; chaque ligne est un arbre
d'expression (la même structure qu'avant). Le curseur porte un numéro de
ligne en plus de son chemin et de son indice.

- `Entrée` crée une nouvelle ligne en coupant la ligne courante au curseur.
- Au niveau supérieur (hors d'une structure), les flèches `Haut`/`Bas`
  passent à la ligne précédente/suivante ; dans une structure, elles en
  sortent/y entrent toujours.
- `Retour arrière` en début de ligne la fusionne avec la précédente ;
  `Suppr` en fin de ligne fusionne la suivante.
- Chaque ligne est présentée, lue et transcrite en braille séparément ; la
  barre d'état lit la ligne **courante**, et `Calculer` la calcule.

## Le format `.dvm`

`.dvm` (document DisViMat) est le format d'enregistrement propre au projet.
Contrairement à l'export XHTML — un format de présentation —, il stocke
l'arbre **exactement** : enregistrer puis rouvrir est un aller-retour sans
perte. C'est du JSON : inspectable et à diff propre dans git.

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

- `language` et `profile` consignent avec quoi le document a été écrit, pour
  rétablir la bonne parole, le bon braille et le bon niveau.
- Chaque nœud est l'un de `{"char": …}`, `{"sign": <id>}` ou
  `{"structure": <id>, "slots": [...]}` ; les ids sont ceux du catalogue,
  les mêmes identifiants stables que tout le reste.
- `version` protège la compatibilité : une version inconnue est refusée avec
  une erreur claire plutôt que mal lue.

## Utilisation

**Bureau** — menu Fichier : Nouveau, Ouvrir (`Ctrl+O`), Enregistrer
(`Ctrl+S`) ; la boîte de dialogue filtre `*.dvm`. Importer/Exporter du XHTML
et Exporter en braille restent dans le même menu.

**Web** — les boutons *Ouvrir (.dvm)* et *Enregistrer (.dvm)* ; enregistrer
télécharge le `.dvm`, ouvrir relit un fichier choisi dans la session.

## Dans le code

[`core/dvm.py`](../../src/disvimat/core/dvm.py) fournit `to_dvm(lines,
language=…, profile=…)` et `from_dvm(text) -> DvmDocument`. Le modèle de
document est dans [`core/document.py`](../../src/disvimat/core/document.py) ;
`Document.lines` est la liste des lignes, et `Editor.load_lines(lines)`
remplace le contenu (annulable). L'aller-retour et les opérations de ligne
sont couverts par `tests/test_dvm.py` et `tests/test_multiline.py`.
