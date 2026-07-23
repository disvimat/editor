# DISVIMAT — Éditeur scientifique accessible

**Langues :** [English](../en/README.md) · [Español](../es/README.md) · [Français](../fr/README.md)

DISVIMAT est un éditeur scientifique (mathématiques, et chimie plus tard)
destiné aux personnes aveugles et malvoyantes. Il fonctionne **sur le
bureau** et **sur le web**, en partageant un noyau unique, et présente
chaque expression de quatre façons : à l'écran, oralisée, en braille et
dans des fichiers exportables.

- [Architecture](ARCHITECTURE.md) — comment le projet est construit, et pourquoi.
- [Tables](TABLES.md) — les données qui régissent le comportement de l'éditeur.
- [Format de document](DOCUMENT.md) — documents multi-lignes et le format `.dvm`.
- [État](STATUS.md) — ce qui est fait et ce qui manque.
- [MathCAT](MATHCAT.md) — le moteur externe de parole et de braille.

## Prérequis

- Python 3.12 ou plus récent.
- Pour l'interface de bureau : wxPython (installé automatiquement).
- Recommandé sous Windows : le lecteur d'écran [NVDA](https://www.nvaccess.org/).

## Installation

```bash
python -m venv .venv
.venv/bin/pip install -e ".[desktop,web,dev]"   # Windows : .venv\Scripts\pip
```

Sous Windows, il suffit de double-cliquer sur `arrancar.bat`, qui crée
l'environnement la première fois puis lance l'éditeur de bureau.

## Lancement

```bash
# Bureau
python -m disvimat.desktop

# Web (ouvrir ensuite http://127.0.0.1:8000/)
python -m disvimat.web.app
```

Deux variables d'environnement configurent les deux interfaces :

| Variable | Signification | Valeurs |
|---|---|---|
| `DISVIMAT_LANG` | langue de l'interface et de la voix | `en` (par défaut), `es`, `fr` |
| `DISVIMAT_PROFILE` | profil d'utilisateur (A7) | `beginner`, `intermediate`, `advanced`, `exam` |
| `DISVIMAT_KEYMAP` | profil clavier — commandes d'un autre éditeur | `lambda`, `edico` (voir `data/keymaps/`) |
| `DISVIMAT_DATA` | répertoire des tables | un chemin ; `data/` par défaut |

Sur le web, la langue est aussi un paramètre : `http://127.0.0.1:8000/?language=fr`.

## La parole et le lecteur d'écran

L'éditeur **oralise chaque action** via votre lecteur d'écran (NVDA, JAWS)
ou SAPI : le signe ou la structure insérés, la case atteinte, le résultat
d'un calcul et le mot terminé par une espace. Il envoie aussi la ligne
courante à l'afficheur braille connecté.

Cela nécessite `accessible_output2`, installé par l'extra `[desktop]`. S'il
manque, l'éditeur fonctionne toujours, mais le retour n'apparaît que dans la
barre d'état, que le lecteur d'écran ne lit pas de lui-même.

## Touches

Les noms de touches sont canoniques et ne sont jamais traduits : ils sont
donc identiques dans toutes les langues et dans les deux interfaces.

| Touches | Action |
|---|---|
| `0-9`, lettres | Insérer du texte |
| `+` `-` `*` `/` `=` `<` `>` `%` `,` | Insérer le signe correspondant |
| `Ctrl+F` | Fraction |
| `Ctrl+R` / `Ctrl+Shift+R` | Racine carrée / racine d'indice |
| `Ctrl+P` / `Ctrl+B` | Puissance / indice |
| `Tab` | Case suivante de la structure |
| `←` `→` `Origine` `Fin` | Déplacer le curseur |
| `↓` `↑` | Entrer dans / sortir d'une structure |
| `Suppr` / `Retour arrière` | Supprimer (une structure est supprimée en entier) |
| `Ctrl+Z` / `Ctrl+Y` | Annuler / rétablir |
| `Ctrl+L` / `Ctrl+Shift+L` | Lire l'élément / toute la ligne |
| `Ctrl+Entrée` | Calculer le résultat |
| `Ctrl+I` / `Ctrl+E` | Importer / exporter du XHTML (bureau) |
| `Ctrl+6` | Fenêtre braille (bureau) |

Le pavé numérique porte aussi `+`, `−`, `×` et `÷` (ce dernier insère une
fraction).

## Premiers pas

Saisissez `1`, `+`, `Ctrl+F`, `2`, `Tab`, `3`. L'écran affiche `1+(2∕3)`,
la ligne se lit « 1 plus fraction 2 sur 3 fin de fraction », et
`Ctrl+Entrée` répond « résultat : 5/3 » sous forme de valeur exacte.

## Développement

```bash
.venv/bin/ruff check .      # style
.venv/bin/mypy              # typage strict du noyau
.venv/bin/pytest            # tests
```

Le code source — identifiants, commentaires et clés des tables — est écrit
**en anglais**, afin que chacun puisse contribuer. Tout ce que l'utilisateur
lit ou entend vit dans les tables de `data/` et s'y traduit, jamais dans le
code. Voir [TABLES.md](TABLES.md).

## Licence

GPL-2.0-only. Auteur : Carlos Daniel Ondo Angue (info@iataccess.org).
