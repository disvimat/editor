# Les tables — modifier l'éditeur sans écrire de code

**Langues :** [English](../en/TABLES.md) · [Español](../es/TABLES.md) · [Français](../fr/TABLES.md)

Tout ce que l'éditeur fait d'un signe — la touche qui l'insère, la façon
dont il est dessiné, oralisé et transcrit — provient des tables JSON de
`data/`.

## L'enveloppe commune

Toutes les tables ont la même forme :

```json
{
  "table": "labels",
  "version": 1,
  "language": "fr",
  "entries": [ { "id": "plus", "label": "plus" } ]
}
```

- `language` vaut `null` pour les tables indépendantes de la langue ;
  celles qui en dépendent portent en plus le suffixe dans le nom du
  fichier : `labels.fr.json`.
- Chaque `id` renvoie au catalogue `elements.json` et respecte
  `[a-z][a-z0-9_]*`. **Les identifiants ne sont jamais traduits** : ce sont
  les repères stables vers lesquels pointe tout le système.

## Les tables

| Fichier | Module initial | Contenu |
|---|---|---|
| `elements.json` | (décision « a ») | catalogue : id, type, catégorie, MathML/Unicode, arité, niveau |
| `keys_signs.json` | A2 | signe ou structure → frappe |
| `keys_commands.json` | A3 | commande → frappe |
| `keys_numpad.json` | A4 | équivalents du pavé numérique |
| `profiles.json` | A7 | profils → niveau maximal et verrou de calculatrice |
| `glyphs.json` | B1 | glyphe et gabarit linéaire |
| `labels.<langue>.json` | B2 | étiquette orale (avec `parts` pour les structures) |
| `messages.<langue>.json` | — | messages du programme (erreurs de calcul…) |
| `ui.<langue>.json` | E6 | chaînes d'interface (menus, boutons) |
| `br6.<langue>.json` | B5 | cellules braille par élément |
| `br6_text.<langue>.json` | B5 | cellules braille par lettre et par chiffre |

## Recettes courantes

### Ajouter un signe

1. Dans `elements.json`, ajoutez l'élément avec son `unicode` (et `mathml`
   s'il s'agit d'une structure, ainsi que son `arity`) :
   ```json
   { "id": "infinity", "type": "sign", "category": "arithmetic", "unicode": "∞", "level": 3 }
   ```
2. Donnez-lui une touche dans `keys_signs.json`, un glyphe dans
   `glyphs.json` et une étiquette dans **tous** les `labels.<langue>.json`.
3. Ajoutez ses cellules braille dans `br6.es.json`.
4. Lancez `pytest` : les tests d'intégrité vous diront ce qui manque.

### Modifier un raccourci

Modifiez la valeur `keys` dans la table concernée. Les noms sont canoniques
(`Ctrl+F`, `Left`, `NumAdd`) et identiques sur le bureau et sur le web. Les
tests refusent une frappe attribuée deux fois.

Une frappe peut être un **accord** : une séquence séparée par des virgules
comme `"Ctrl+G, P"` (la convention d'EDICO pour les lettres grecques et les
titres). La première frappe met le clavier en attente ; la suivante la
complète. Un accord et une frappe simple ne peuvent pas se chevaucher :
`"Ctrl+G"` et `"Ctrl+G, P"` ensemble sont refusées, car après `Ctrl+G`
l'éditeur ne peut faire qu'une seule chose.

### Réattribuer une touche en tant qu'utilisateur, sans conflit

L'utilisateur ne modifie pas les tables livrées. Ses réattributions
personnelles vivent dans un profil de clavier que l'éditeur charge **en
dernier** : une attribution de l'utilisateur l'emporte donc sur les tables
par défaut, sur un profil de compatibilité (Lambda, EDICO) et sur les
extensions. Le fichier est `$DISVIMAT_USER_KEYMAP` ou
`~/.disvimat/user_keys.json`.

L'outil `rebind` l'édite en toute sûreté :

```bash
python -m disvimat.tools.rebind show "Ctrl+F"      # ce que fait une frappe
python -m disvimat.tools.rebind set fraction "Ctrl+B"
python -m disvimat.tools.rebind clear fraction
python -m disvimat.tools.rebind list
```

Avant d'enregistrer, il **refuse** une attribution impossible (une commande
inconnue, ou un accord qui en masquerait un autre) et **avertit** lorsque la
nouvelle frappe était déjà utilisée par une autre commande, en nommant celle
qui la perd — pour qu'une réattribution soit délibérée, jamais silencieuse.

### Ajouter une langue

Copiez `labels.en.json`, `messages.en.json` et `ui.en.json` sous le code de
votre langue, renseignez `"language"` dans chacun et traduisez **les
valeurs uniquement**. Ce que vous ne traduisez pas se replie sur l'anglais
au lieu d'échouer.

Le braille, lui, est différent : voir ci-dessous.

### Ajouter une table braille

`br6.<langue>.json` et `br6_text.<langue>.json` doivent être produits par
quelqu'un qui connaît la notation mathématique braille du pays concerné.
Ces tables **ne se replient pas** sur une autre langue, et c'est
volontaire : donner du braille espagnol à un lecteur français serait
erroné. Sans elles, l'application désactive simplement ses fonctions
braille.

> **Important.** Les valeurs actuelles de `br6.es.json` sont
> **provisoires** et doivent être vérifiées au regard de la notation
> mathématique braille de la CBE (Comisión Braille Española) avant tout
> usage en classe. L'export braille est en Unicode (U+2800…, `.brl`).
> provisoire.

## Comment les structures se décrivent

Une structure possède des cases et se décrit trois fois :

- **Glyphe**, avec un `template` linéaire où `{1}`, `{2}`… sont les cases :
  `"({1}∕{2})"` présente la fraction comme `(2∕3)`.
- **Étiquette**, avec des `parts` (`start`, `separator`, `end`) qui
  composent la lecture linéaire : « fraction 2 sur 3 fin de fraction ».
  `start` peut être omis, ce qui rend « x puissance 2 » naturel.
- **Braille**, avec les mêmes trois `parts`, chacune portant une liste de
  cellules.

Une cellule s'écrit avec ses points : `"1-4-5"` ; `""` est la cellule
vide.

## Intégrité

`tests/test_integrity.py` vérifie, à chaque construction, que :

1. chaque entrée renvoie à un identifiant existant dans `elements.json` ;
2. chaque signe et chaque structure possède un glyphe et des cellules
   braille, et chaque élément possède une étiquette dans toutes les
   langues ;
3. toutes les langues définissent exactement les mêmes identifiants de
   messages et d'interface ;
4. aucune frappe n'est attribuée deux fois, même d'une table à l'autre.

Une table cassée arrête la construction, pas l'utilisateur.
