# Extensions — enrichir l'éditeur sans toucher au noyau (module A5)

**Langues :** [English](../en/ADDONS.md) · [Español](../es/ADDONS.md) · [Français](../fr/ADDONS.md)

Une extension est du Python ordinaire qui **déclare ce qu'elle apporte**.
L'éditeur l'intègre comme si elle était native : même résolution des
touches, même parole, même annulation. Ajouter une fonction n'oblige jamais
à modifier l'éditeur.

## L'extension minimale

```python
def register(registry):
    registry.add_command(
        id="compter",
        run=lambda editor: f"{len(editor.document.current_line())} éléments",
        keys="Ctrl+Alt+C",
        labels={"fr": "compter la ligne", "en": "count the line"},
    )
```

C'est tout. Au démarrage, l'éditeur :

1. ajoute `compter` au **catalogue** comme commande,
2. lui attribue la **touche** `Ctrl+Alt+C`,
3. enregistre son **étiquette orale** par langue,
4. et la place dans la table de répartition, à côté des commandes natives.

## Comment elles sont trouvées

**Un dossier de scripts** — la voie rapide pour un enseignant ou un
utilisateur :

```
set DISVIMAT_ADDONS=C:\Users\moi\disvimat-addons
```

Chaque `.py` de ce dossier possédant une fonction `register(registry)` est
chargé au démarrage. C'est le « concepteur de scripts » du document
initial.

**Un paquet installable** — la façon normale d'en distribuer une. Dans son
`pyproject.toml` :

```toml
[project.entry-points."disvimat.addons"]
mon-extension = "mon_extension:register"
```

## Ce qu'elle peut apporter

| Appel | Apporte |
|---|---|
| `registry.add_command(id, run, keys=…, labels=…)` | une commande avec touche et parole |
| `registry.add_exporter(id, extension, dump, labels=…)` | un format d'export |

`run(editor)` reçoit l'éditeur : elle peut lire et modifier le document
(`editor.document`), insérer du contenu (`editor.type_character`), et
renvoie **le texte à oraliser**.

## Une panne n'arrête jamais l'éditeur

- Une extension qui casse **au chargement** est consignée dans
  `registry.errors` et les autres se chargent quand même.
- Une commande qui lève une exception **à l'exécution** est contenue :
  l'utilisateur entend « l'extension n'a pas pu s'exécuter » (traduisible,
  dans la table `messages`) et l'éditeur continue de fonctionner.

Les deux sont couverts par `tests/test_addons.py`.

## Un exemple complet

[`examples/addons/count_elements.py`](../../examples/addons/count_elements.py)
est une extension réelle et fonctionnelle qui compte les éléments de la
ligne courante, avec des étiquettes en anglais, espagnol et français.

## Les désactiver

`create_editor(addons=False)` construit un éditeur sans aucune extension,
ce que fait la suite de tests pour rester déterministe.
