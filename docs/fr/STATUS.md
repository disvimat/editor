# État du projet — ce qui existe et ce qui manque

**Langues :** [English](../en/STATUS.md) · [Español](../es/STATUS.md) · [Français](../fr/STATUS.md)

Audit au regard de la liste des modules du document initial du projet
([README.md](../BRIEF.es.md)). Mis à jour le 21/07/2026.

Légende : **fait** · **partiel** — utilisable mais incomplet · **à faire** — non commencé.

## Résumé

L'éditeur est utilisable dès aujourd'hui pour l'**arithmétique linéaire et
l'algèbre élémentaire**, sur le **bureau** (wxPython + NVDA) et sur le
**web** (FastAPI + MathML natif), avec l'oralisation en anglais, espagnol
et français, le braille six points en espagnol, l'import et l'export
XHTML, l'export braille Unicode et une calculatrice à arithmétique exacte dotée d'un
verrou pour l'enseignant.

Les deux manques les plus importants sont le **module complémentaire NVDA**
(afficheurs braille et voix directe, modules B3/E1) et les **structures
bidimensionnelles** (matrices et tableaux, modules A10/B7).

## A) Modules de fonctionnement

| Module | État | Remarques |
|---|---|---|
| A1 filtre Unicode/MathML → DisvimatEditor | **fait** | Aller-retour vérifié par les tests |
| A2 signes et structures → frappes | **fait** | `keys_signs.json` ; les frappes peuvent être des **accords** (`"Ctrl+G, P"`, la convention d'EDICO) résolus par une petite machine à états |
| A3 commandes → frappes | **partiel** | Table faite ; la grammaire des *conditions* n'est pas implémentée. Le champ `condition` existe mais `Keyboard` ne charge que les entrées inconditionnelles : une attribution conditionnelle ne ferait rien — ni fonctionner, ni protester. Tant que la grammaire n'existe pas, `integrity.unsupported_conditions` **casse la construction** si une table l'emploie, plutôt que de laisser l'attribution disparaître en silence |
| — profils de clavier et réattribution utilisateur | **fait** | Les profils de compatibilité (`data/keymaps/`, Lambda/EDICO) se chargent par-dessus les tables par défaut ; un profil de clavier par utilisateur (`$DISVIMAT_USER_KEYMAP` ou `~/.disvimat/user_keys.json`) se charge en dernier et l'emporte. L'outil `rebind` réattribue une touche avec détection de conflits (refuse les commandes inconnues et les chevauchements d'accords, avertit lorsqu'une frappe est volée) |
| A4 touches alternatives (pavé numérique) | **partiel** | Quatre attributions seulement ; le schéma complet reste à faire. Elles fonctionnent désormais sur **les deux** interfaces : le navigateur signale le `/` du pavé comme touche `"/"`, comme celui de la rangée principale, si bien que le web y voyait un signe de division là où le bureau insérait une fraction. Les deux adaptateurs tirent maintenant leurs noms de `keys_platform.json` |
| A5 concepteur de scripts / modules | **fait** | [Extensions](ADDONS.md) : une fonction `register(registry)` ajoute commandes (touche, parole, code) et exports, découvertes comme paquets installés ou fichiers `.py` dans `DISVIMAT_ADDONS`. Les pannes sont contenues |
| A6 fichier d'aide (modifiable, par langue) | **à faire** | |
| A7 configurateur de profils | **partiel** | `profiles.json` limite les éléments par niveau et verrouille la calculatrice, et **le profil voyage dans le `.dvm`** : ouvrir un document construit l'éditeur que ce document décrit, si bien qu'un examen préparé par l'enseignant impose ses restrictions sur n'importe quelle machine. Une interface d'édition des profils manque encore |
| A8 calculatrice | **partiel** | Arithmétique exacte des fractions, priorités, puissances et racines exactes ; ni variables, ni fonctions, ni trigonométrie |
| A9 verrou de calculatrice | **fait** | `calculator: false` dans le profil (profil `exam`) |
| A10 structures bidimensionnelles (tableaux, matrices, déterminants) | **partiel** | Matrices : insérer (`Ctrl+Maj+M`), navigation en grille, ajouter ligne/colonne (`Alt+Bas`/`Alt+Droite`), lecture ligne par ligne, MathML `<mtable>` aller-retour, `.dvm`. Déterminants/tableaux réutilisent le même nœud |
| A11 algorithmes bidimensionnels | **à faire** | |

## B) Modules de présentation

| Module | État | Remarques |
|---|---|---|
| B1 table de glyphes | **fait** | Avec gabarits linéaires pour les structures |
| B2 étiquettes / oralisation par langue | **fait** | Voix d'édition en anglais, espagnol et français (nos tables) ; lecture de l'expression entière via [MathCAT](MATHCAT.md) en anglais et espagnol |
| B3 br8 (NVDA et afficheurs braille) | **partiel** | Le bureau oralise chaque action via le lecteur d'écran et envoie la ligne courante à l'afficheur braille connecté, par le contrôleur NVDA/JAWS (`accessible_output2`). La *saisie* BR8 et un module dédié restent à faire |
| B4 fenêtre de présentation graphique | **fait** | Contrôle texte natif (bureau) et MathML natif (web) |
| B5 transcripteur braille | **fait (moteurs externes)** | Le braille provient d'une échelle ([BRAILLE.md](BRAILLE.md)) : [MathCAT](MATHCAT.md) pour les mathématiques (CMU, UEB), [liblouis](BRAILLE.md) pour le texte (tables officielles, p. ex. français), nos tables `br6` en dernier recours. Vérifié sous Python 3.13 64 bits |
| B6 fenêtre br6 | **partiel** | La fenêtre affiche et suit la transcription ; la navigation *à l'intérieur* de la fenêtre braille manque |
| B7 présentation des structures 2D | **partiel** | Forme linéaire `[a,b;c,d]` à l'écran et `<mtable>` natif sur le web ; une fenêtre 2D dédiée reste à faire |
| B8 présentation des algorithmes 2D | **à faire** | |
| B9 messages en langue des signes | **à faire** | |

## C) Modules d'exportation

| Module | État | Remarques |
|---|---|---|
| C1 XHTML | **fait** | Du MathML que les navigateurs rendent et que les lecteurs oralisent |
| C2 PDF | **à faire** | Prévu via WeasyPrint, en réutilisant l'export XHTML |
| C3 export braille | **fait** | Exporte du braille Unicode (U+2800…, `.brl`, UTF-8) depuis le moteur actif (MathCAT / liblouis / tables). La conversion ASCII reste dans le code mais n'est plus le format d'export |
| C4 MP3 | **à faire** | |

## D) Modules d'importation

| Module | État | Remarques |
|---|---|---|
| D1 XHTML | **fait** | Annulable ; erreurs claires pour le contenu non pris en charge |
| D2 LaTeX | **à faire** | |

## E) Modules d'extension

| Module | État |
|---|---|
| E6 internationalisation | **fait** — anglais, espagnol, français ; ajouter une langue revient à modifier du JSON |
| E1 saisie par clavier br8 d'afficheur braille | **à faire** |
| E2 clavier braille virtuel | **à faire** |
| E3 collections de formules | **à faire** |
| E4 dictionnaire mathématique | **à faire** |
| E5 réserve de théorèmes | **à faire** |
| E7 saisie manuscrite | **à faire** |
| E8 symboles personnalisés | **à faire** |
| E9 commande vocale | **à faire** |
| E10–E11 graphiques statistiques et de fonctions | **à faire** |
| E12 sonification des graphiques | **à faire** |
| E13 exercices interactifs | **à faire** |
| E14 jeux mathématiques | **à faire** |

## F) Version éditeur de chimie

F1 à F6 sont tous **à faire**. Le terrain est préparé : le catalogue
comporte déjà un champ `category`, si bien que les signes et structures de
chimie s'ajoutent en tant que données, et non en tant que code.

## Manques transversaux à connaître

Ils ne figurent pas dans la liste initiale des modules mais comptent pour
un usage réel :

1. ~~Pas de format de document propre.~~ **Fait :** le format `.dvm`
   ([DOCUMENT.md](DOCUMENT.md)) enregistre et rouvre l'arbre exact, avec la
   langue et le profil d'écriture. Enregistrer/Ouvrir sur bureau et web.
2. ~~Un document tient sur une seule ligne.~~ **Fait :** les documents sont
   désormais **multi-lignes** — `Entrée` crée une ligne, les flèches
   passent d'une ligne à l'autre au niveau supérieur, et chaque ligne est
   présentée, lue et braillée séparément.
3. ~~Pas de module NVDA : la voix repose sur la barre d'état.~~ **Corrigé :**
   le bureau oralise désormais chaque action via le lecteur d'écran et
   envoie le braille à l'afficheur. Un module dédié reste nécessaire pour
   la *saisie* au clavier BR8 (E1).
4. **Les sessions web vivent en mémoire.** Elles ne croissent plus sans
   limite : elles expirent après inactivité (`DISVIMAT_SESSION_TTL`, deux
   heures par défaut) et leur nombre est borné (`DISVIMAT_MAX_SESSIONS`,
   500), la moins récemment utilisée étant écartée. Quand une session
   expire, la page en ouvre une autre et **l'annonce à voix haute**, pour
   ne laisser personne saisir dans un éditeur devenu muet. Il n'y a
   toujours ni authentification ni persistance : le document est perdu au
   redémarrage du processus.
5. **Le braille demande une validation experte.** Le moteur est terminé,
   les valeurs ne le sont pas : elles doivent être confrontées à la
   notation mathématique braille de la CBE avant tout usage en classe.
6. **Tests d'accessibilité automatisés : la moitié existe désormais.** Le
   contrat du bureau avec le lecteur d'écran **est** vérifié en intégration
   continue : un travail sous **Windows** avec wxPython construit la vraie
   fenêtre et contrôle que chaque action est oralisée (et pas seulement
   affichée dans la barre d'état), que le curseur se pose là où le noyau l'a
   mis, que la ligne courante parvient à l'afficheur braille et qu'aucun
   braille n'est envoyé sans moteur. L'intégration continue ne tournait que
   sous Linux, sans wxPython : ces tests se sautaient entièrement et le
   build passait au vert sans rien avoir testé ; `DISVIMAT_REQUIRE_DESKTOP=1`
   transforme désormais ce saut en échec là où wxPython doit être présent.
   Le **web** aussi : la structure dont dépend un lecteur d'écran est
   contrôlée sur la page rendue (une seule région `aria-live`, la barre
   d'état délibérément en dehors, `role="application"` avec nom et
   instructions, références `aria-*` qui aboutissent, identifiants uniques,
   lien d'évitement qui mène quelque part, ordre des titres, zoom autorisé,
   `lang` par langue). Et `editor.js` est passé d'aucun test à une suite
   **vitest + jsdom** qui évalue le vrai fichier dans la vraie page et le
   pilote par événements : le `/` du pavé numérique, l'ordre des frappes
   (une seule requête en vol), la région vive et la reprise oralisée d'une
   session expirée.
   Il manque encore : un passage d'**axe-core dans un vrai navigateur** —
   jsdom ne peut donner ni contraste ni visibilité calculée, l'y faire
   serait une fausse assurance — et des tests NVDA scriptés (Guidepup).

## Prochaines étapes suggérées

Le braille/parole (MathCAT + liblouis) et la couche document (`.dvm`,
multi-lignes) sont faits. Ce qui reste, par ordre d'impact :

1. Module complémentaire NVDA pour les afficheurs braille et la voix
   directe (B3/E1) ; le module NVDA de MathCAT est la référence à suivre.
2. Structures bidimensionnelles (A10/B7) : matrices et tableaux.
3. Export PDF (C2) et MP3 (C4).
4. Texte et mathématiques mêlés dans un document (le braille de texte de
   liblouis couvre alors les parties en prose).
