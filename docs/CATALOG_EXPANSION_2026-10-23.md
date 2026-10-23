# Extension du catalogue Anime-Sama TV — 23 octobre 2026

## Résultat
- Avant : **234 séries** indexées dans le moteur de recherche vérifié.
- Après : **602 séries** avec un ID IMDb unique, soit **+368 séries**. Aucun des 234 identifiants de départ supprimé.
- Index de noms du site : **1 588 entrées Anime-Sama** plus un titre alternatif, utilisées pour repérer les correspondances. Un nom non confirmé n'est jamais automatiquement ajouté à la recherche avec un faux IMDb.
- Recherche : docs/catalog/series/as_search.json ; le fichier reste anime-only (type=series) et ne contient aucun lien de flux ou fichier vidéo.
- Manifest du catalogue : docs/manifest.json version **0.4.0**. Le moteur de lecture Anime-Sama (manifest de la racine version 1.1.61) n'est pas modifié.

## Accueil : cinq nouveaux rayons
- **Action & aventure** — 36 affiches classées par note des métadonnées.
- **Magie & fantasy** — 36 affiches, uniquement séries documentées en genre Fantasy.
- **Romance & émotions** — 36 affiches vérifiées Romance.
- **Comédies** — 36 affiches documentées Comedy.
- **Imaginaire & science-fiction** — 36 affiches regroupant Sci-fi et Sci-fi & Fantasy.
- Les rayons déjà présents sont conservés : **Les classiques (24), Derniers ajouts (64), Sorties récentes (60)**, ainsi que Recherche.
- Des séries peuvent appartenir à plusieurs rayons : c'est une catégorisation, et non des fiches dupliquées dans le catalogue de recherche.
- La mise à jour des rayons sur une TV qui possède déjà le manifeste en cache peut nécessiter sa prochaine actualisation. **Ne pas effacer les données de l'application pour obtenir les nouveaux rayons.**

## Vérifications
- Trois vagues de 260 recherches Cinemeta, candidates acceptées uniquement avec forte concordance du titre, métadonnées série animée, IMDb et épisodes réels.
- Vérification de genres Cinemeta sur le catalogue élargi : **591 séries disposent de métadonnées « Animation » cohérentes et avec épisodes** ; **11 entrées historiques** présentent un genre absent ou incohérent et sont préservées mais exclues des nouveaux rayons. Elles nécessitent un audit des identifiants anciens séparé. Aucun des 368 nouveaux ID ne figure dans ces 11 exceptions.
- npm run audit:catalog : vérifie identifiants uniques, type=series, affiches HTTPS, fidélité des affiches/titres des rayons par rapport à la recherche et exactitude des genres. **Réussi**.
- **10/10 affiches** nouvelles contrôlées en HTTP HEAD : réponse 200.
- Résolution de flux sur quatre séries nouvellement indexées : **Beastars (4/4), Grimoire of Zero (2/2), Deadman Wonderland (4/4), Yasuke (4/4)**. Ces essais sur PC ne prétendent pas avoir joué chaque vidéo de chacune des 602 séries.
- Le code Android, les préférences de lecture, la reprise et le mode VF/1080p déjà validé sur Qilive ne sont pas modifiés.

## Relancer les audits
Depuis le dépôt fournisseur :
- `python scripts/expand_search_index.py --queries 260` pour auditer de nouveaux candidats et élargir progressivement la recherche.
- `npm run build:genres` pour reconstruire les rayons depuis des métadonnées vérifiées.
- `npm run audit:catalog` pour vérifier les fichiers avant publication.
- `npm run smoke:anime-sama` pour contrôler la résolution de sources connues.

Important : scripts/build_classics.py et scripts/build_catalog.py possèdent d'anciennes instructions de régénération du manifeste ; ne pas les lancer aveuglément après cette extension car ils pourraient écraser la liste des rayons. Le moteur de lecture reste déployé depuis le manifeste racine.

## Publication
Dépôt : https://github.com/JoeSm0ke/Nuvio-AnimeSama-Qilive sur la branche main. Les pages statiques sont servies via https://joesm0ke.github.io/Nuvio-AnimeSama-Qilive/.
