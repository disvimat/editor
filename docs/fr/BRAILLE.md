# Braille — comment il est produit

**Langues :** [English](../en/BRAILLE.md) · [Español](../es/BRAILLE.md) · [Français](../fr/BRAILLE.md)

DISVIMAT n'écrit pas de tables braille à la main. Il emploie les deux
moteurs qu'utilisent les technologies d'assistance comme NVDA, chacun pour
ce qu'il fait de mieux, avec un repli progressif :

```
braille mathématique  →  MathCAT      (CMU, UEB, Nemeth…)   ┐
braille de texte      →  liblouis     (tables officielles)  ├─ échelle, dans l'ordre
dernier recours       →  nos tables   (br6.*.json)          ┘
```

## Pourquoi deux moteurs

- **[MathCAT](MATHCAT.md)** lit la *notation* mathématique (MathML) et
  produit un braille mathématique normatif : CMU pour l'espagnol, UEB pour
  l'anglais. C'est le braille adapté aux expressions que l'éditeur produit.
- **liblouis** traduit du *texte* en braille avec des tables officielles et
  maintenues pour de très nombreuses langues. C'est le traducteur braille
  standard derrière NVDA, Orca et BrailleBlaster. Il gère les parties de
  texte littéraire et fournit du braille pour les langues que MathCAT ne
  couvre pas (par exemple le braille de texte français).

Ils sont complémentaires, non concurrents — NVDA utilise les deux. Ici
MathCAT fournit le braille d'une expression mathématique entière ; liblouis
est la couche de braille de texte en dessous ; nos tables `br6` (dont les
valeurs espagnoles sont provisoires) ne sont que le dernier recours quand
aucun moteur n'est installé.

## L'échelle dans le code

`create_outputs` dans [`backends.py`](../../src/disvimat/backends.py)
choisit le moteur braille par langue :

1. MathCAT s'il est installé et couvre la langue.
2. sinon liblouis s'il est installé et possède une table de texte pour la
   langue.
3. sinon nos tables `br6`.
4. sinon le braille est désactivé pour cette langue (jamais celui d'une
   autre).

Chaque couche est son propre adaptateur derrière le port `BrailleProvider`
([`core/output.py`](../../src/disvimat/core/output.py)) :
[`core/mathcat.py`](../../src/disvimat/core/mathcat.py),
[`core/liblouis.py`](../../src/disvimat/core/liblouis.py),
[`core/transcription/braille.py`](../../src/disvimat/core/transcription/braille.py).

## Installer liblouis

liblouis n'est pas un simple `pip install` : c'est une bibliothèque native
plus un répertoire de tables. Pour Windows 64 bits, un installateur en une
commande existe :

```bash
python scripts/install_liblouis.py
```

Il télécharge le `liblouis.dll` officiel et les tables dans
`site-packages/disvimat_liblouis/`, puis vérifie une traduction en
espagnol. Sous Linux/macOS, installez liblouis avec le gestionnaire de
paquets (`apt install liblouis`, `brew install liblouis`) et faites pointer
`LIBLOUIS_DLL` et `LOUIS_TABLEPATH` vers la bibliothèque et ses tables.

Vérifiez :

```python
from disvimat.core.liblouis import is_available
print(is_available())          # True dès que bibliothèque et tables sont trouvées
```

## Choix de la table

La table de texte par langue est une petite carte modifiable dans
`core/liblouis.py` (`TEXT_TABLES`) : espagnol → `es-g1.ctb`, anglais →
`en-ueb-g1.ctb`, français → `fr-bfu-comp6.utb`. Le grade 1 (non abrégé) est
le choix sûr à côté des mathématiques. Réorienter une langue, ou en ajouter
une, revient à modifier cette carte — les tables sont celles de liblouis,
pas les nôtres.

## Bon à savoir

- **Vérifié** sous Python 3.13 64 bits (Windows) : liblouis produit du
  braille Unicode (mode `dotsIO | ucBrl`) avec des tables officielles :
  espagnol `es-g1`, anglais `en-ueb-g1`, français `fr-bfu-comp6`.
- **liblouis est un moteur de texte.** Lui donner une expression
  mathématique entière brailleraient les symboles littéralement ; c'est
  pourquoi le braille mathématique passe par MathCAT. liblouis compte pour
  les parties de texte, comme repli, et pour les langues de texte seul.
- **Déterminisme des tests.** `DISVIMAT_NO_LIBLOUIS=1` (et
  `DISVIMAT_NO_MATHCAT=1`) forcent nos tables même si les moteurs sont
  installés ; la suite de tests fixe les deux pour que les résultats soient
  identiques avec ou sans les bibliothèques natives.
