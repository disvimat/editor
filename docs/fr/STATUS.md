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
XHTML, l'export .BRA et une calculatrice à arithmétique exacte dotée d'un
verrou pour l'enseignant.

Les deux manques les plus importants sont le **module complémentaire NVDA**
(afficheurs braille et voix directe, modules B3/E1) et les **structures
bidimensionnelles** (matrices et tableaux, modules A10/B7).

## A) Modules de fonctionnement

| Module | État | Remarques |
|---|---|---|
| A1 filtre Unicode/MathML → DisvimatEditor | **fait** | Aller-retour vérifié par les tests |
| A2 signes et structures → frappes | **fait** | `keys_signs.json` |
| A3 commandes → frappes | **partiel** | Table faite ; la grammaire des *conditions* n'est pas implémentée (le champ `condition` existe et les entrées conditionnelles sont ignorées) |
| A4 touches alternatives (pavé numérique) | **partiel** | Quatre attributions seulement ; le schéma complet reste à faire |
| A5 concepteur de scripts / modules | **à faire** | Le noyau constitue déjà l'API publique nécessaire |
| A6 fichier d'aide (modifiable, par langue) | **à faire** | |
| A7 configurateur de profils | **partiel** | `profiles.json` limite les éléments par niveau et verrouille la calculatrice ; aucune interface d'édition des profils |
| A8 calculatrice | **partiel** | Arithmétique exacte des fractions, priorités, puissances et racines exactes ; ni variables, ni fonctions, ni trigonométrie |
| A9 verrou de calculatrice | **fait** | `calculator: false` dans le profil (profil `exam`) |
| A10 structures bidimensionnelles (tableaux, matrices, déterminants) | **à faire** | |
| A11 algorithmes bidimensionnels | **à faire** | |

## B) Modules de présentation

| Module | État | Remarques |
|---|---|---|
| B1 table de glyphes | **fait** | Avec gabarits linéaires pour les structures |
| B2 étiquettes / oralisation par langue | **fait** | Anglais, espagnol et français |
| B3 br8 (NVDA et afficheurs braille) | **à faire** | Nécessite un module complémentaire NVDA dédié |
| B4 fenêtre de présentation graphique | **fait** | Contrôle texte natif (bureau) et MathML natif (web) |
| B5 transcripteur br6 | **partiel** | Le moteur est complet et piloté par tables ; **les valeurs espagnoles sont provisoires et doivent être vérifiées auprès de la CBE** ; pas de table anglaise (UEB) ni française (NMB) |
| B6 fenêtre br6 | **partiel** | La fenêtre affiche et suit la transcription ; la navigation *à l'intérieur* de la fenêtre braille manque |
| B7 présentation des structures 2D | **à faire** | |
| B8 présentation des algorithmes 2D | **à faire** | |
| B9 messages en langue des signes | **à faire** | |

## C) Modules d'exportation

| Module | État | Remarques |
|---|---|---|
| C1 XHTML | **fait** | Du MathML que les navigateurs rendent et que les lecteurs oralisent |
| C2 PDF | **à faire** | Prévu via WeasyPrint, en réutilisant l'export XHTML |
| C3 BRA (braille six points) | **partiel** | Fonctionne ; dépend de la vérification braille, et l'encodage ASCII est le NABCC provisoire |
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

1. **Pas de format de document propre.** Il n'existe ni « enregistrer » ni
   « ouvrir » : les documents ne circulent que par import et export XHTML.
   Un format `.dvm` conservant l'arbre, la langue et le profil est
   nécessaire.
2. **Un document tient sur une seule ligne.** L'arbre contient une séquence
   d'expression ; ni paragraphes, ni lignes multiples, ni texte mêlé aux
   mathématiques.
3. **Pas de module complémentaire NVDA** : la voix repose donc sur la barre
   d'état (bureau) et sur la région `aria-live` (web), au lieu de parler
   directement.
4. **Les sessions web vivent en mémoire** et disparaissent au redémarrage
   du processus ; il n'y a ni authentification ni persistance.
5. **Le braille demande une validation experte.** Le moteur est terminé,
   les valeurs ne le sont pas : elles doivent être confrontées à la
   notation mathématique braille de la CBE avant tout usage en classe.
6. **Les tests d'accessibilité automatisés manquent.** L'intégrité des
   tables est vérifiée en intégration continue, mais il n'y a ni passage
   d'axe-core sur la page web ni tests NVDA scriptés ; l'accessibilité est
   vérifiée à la main.

## Prochaines étapes suggérées

1. Faire vérifier les tables braille par un spécialiste (B5/C3) : peu
   coûteux, à fort impact, et ce ne sont que des données.
2. Module complémentaire NVDA pour les afficheurs braille et la voix
   directe (B3/E1).
3. Format de document propre avec enregistrement et ouverture, et documents
   multi-lignes.
4. Structures bidimensionnelles (A10/B7) : matrices et tableaux.
5. Export PDF (C2) et MP3 (C4).
