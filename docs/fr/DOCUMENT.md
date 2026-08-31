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

- `language` et `profile` ne sont pas une note de bas de page : **ouvrir un
  document construit l'éditeur que ce document décrit**. C'est là le modèle
  de l'examen — l'enseignant enregistre un `.dvm` avec `"profile": "exam"`,
  l'élève l'ouvre sur n'importe quel système et y trouve le niveau limité
  et la calculatrice verrouillée (A7/A9) sans que cette machine sache quoi
  que ce soit de cet examen. L'enregistrement réécrit le profil : la
  restriction survit à l'aller-retour au lieu de durer une seule séance.
- `language` s'impose tout autant, pour une raison précise : le braille
  mathématique est normatif et diffère selon les pays ; lire un document
  espagnol sous un éditeur anglais le transcrirait en UEB et non en CMU.
  La langue de l'**interface** ne change pas : les menus ne doivent pas
  bouger sous les doigts de qui utilise un lecteur d'écran.
- Un profil que l'installation ne connaît pas est refusé comme document
  malformé, sans planter.
- Le verrou est une convention de classe, pas une barrière
  cryptographique : un `.dvm` est du JSON lisible, éditable par qui le
  souhaite. Ce qui est rendu, c'est le fichier, et le trafiquer laisse une
  trace.
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
