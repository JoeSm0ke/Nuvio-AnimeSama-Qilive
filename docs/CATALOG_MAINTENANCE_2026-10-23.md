# Anime-Sama TV — Stabilisation du catalogue (23 octobre 2026)

## Résultat et périmètre
Le catalogue statique **0.4.1** contient **601 séries IMDb distinctes** et conserve les neuf catégories de l'accueil : Les classiques, Action & aventure, Magie & fantasy, Romance & émotions, Comédies, Imaginaire & science-fiction, Derniers ajouts, Sorties récentes et Recherche.

Le décompte **602 / version 0.4.0** figurant dans le rapport historique d'extension était correct lors de sa publication. Cette passe privilégie la justesse des identifiants : 601 fiches aujourd'hui, avec **592 fiches dont le genre Animation et les épisodes ont été revérifiés**, et neuf correspondances antérieures encore signalées comme incomplètes dans Cinemeta. Les neuf entrées incertaines n'apparaissent pas dans les rayons thématiques.

Aucun changement du moteur de lecture Anime-Sama **1.1.61**, de l'application Android, du lecteur VF/VOSTFR, des favoris ou de la reprise. Aucune commande exécutée sur la Qilive.

## Deux associations IMDb incorrectes corrigées
- **Seven Deadly Sins** : l'identifiant `tt0108088` correspond à une série de 1993 dont les épisodes s'intitulent Lust, Pride, etc. La fiche Anime-Sama utilise désormais **`tt3909224`**, The Seven Deadly Sins, anime 2014, genres Animation/Action/Adventure, 124 éléments d'épisodes dans la réponse Cinemeta.
- **The Legend of Hei** : `tt27531070` renvoie à **The Legend of Shen Li**, œuvre différente. En l'absence d'un nouvel identifiant anime-série validé, la fiche est retirée de `as_search` et `as_latest`. Son titre reste trouvable dans l'index brut des noms de l'ancien site ; il n'est plus présenté comme série jouable via un mauvais IMDb.
- Les ID interdits figurent dans `scripts/quarantined-imdb-mappings.json`, vérifiés par `npm run audit:catalog` et exclus de la régénération par `expand_search_index.py` ainsi que `verify_search_metadata.py`. Les caches historiques, même inchangés, ne pourront pas les réintroduire.
- **Attention aux favoris antérieurs :** une liste locale qui aurait mémorisé l'ancien `tt0108088` n'est pas automatiquement migrée. Il faudra éventuellement réajouter l'anime depuis sa nouvelle fiche correcte ; nous ne touchons pas aux profils existants.

## Les scripts de maintenance ne peuvent plus dégrader l'accueil
- `build_classics.py` reconstitue uniquement des classiques connus, à partir des **fiches vérifiées de `as_search`** (titre et affiche), avec garde-fou contre une réponse trop courte. Ne modifie jamais le manifeste.
- `build_catalog.py` reconstruit Derniers ajouts et Sorties récentes par **titre exact normalisé ET affiche identique** au catalogue vérifié. Plus de recherche IMDb approximative dans le script de rafraîchissement. Si les résultats sont insuffisants, aucune des deux rangées n'est publiée.
- `build_site_index.py` bloque désormais une chute anormale de l'index de noms (plus de 15 % par rapport au précédent).
- `build_genre_catalogs.py` préserve la version courante du manifeste ; elle n'est plus ramenée à 0.4.0 par une régénération.
- Les scripts `build_classics.py` et `build_catalog.py` disposent de `--dry-run`.
- Les dépendances Python sont définies dans `scripts/requirements-catalog.txt`, et installées dans un environnement isolé `.venv/` (ignoré par Git). Rien à installer dans Python global.

## Qualité automatisée
- **5 tests unitaires hors réseau** dans `scripts/test_catalog_maintenance.py` : conservation du manifeste, rejets de pages incomplètes, interdiction d'écraser les derniers fichiers corrects et préservation de la version.
- `npm run audit:catalog` : contrôles de cohérence de l'index, des neuf rangées, des genres et des identifiants interdits.
- Le workflow `.github/workflows/catalog-integrity.yml` applique ces contrôles à chaque changement pertinent poussé sur GitHub.
- La mise à jour automatique existante `.github/workflows/update-catalog.yml` (lundi et jeudi) installe ses dépendances, exécute les tests, régénère les fichiers puis **audite avant de publier**. Si une étape échoue, elle ne crée pas de commit.
- Le manifeste public est contrôlé indépendamment de celui du lecteur. Les nouvelles données seront accessibles au prochain rafraîchissement du catalogue par la TV.

## Procédure recommandée sur le PC Windows
Depuis `%LOCALAPPDATA%\\QiliveRemote\\AnimeSama-Published` :

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r scripts\\requirements-catalog.txt
.\\.venv\\Scripts\\python.exe -m unittest discover -s scripts -p test_catalog_maintenance.py -v
.\\.venv\\Scripts\\python.exe scripts\\build_classics.py --dry-run
.\\.venv\\Scripts\\python.exe scripts\\build_catalog.py --dry-run
node scripts\\audit-static-catalog.cjs
```

Aucun de ces tests ne modifie la Qilive. Ne pas lancer de régénération complète ni pousser un fichier produit qui échoue à l'audit. Avant une future montée de version, conserver une sauvegarde des JSON et vérifier le manifeste public après publication.

## Décision
La base Anime-Sama reste **mono-fournisseur**. Franime et les autres fournisseurs sont explicitement exclus de cette passe. L'objectif est la fiabilité d'un fonctionnement déjà validé avec image, son, épisode et reprise sur la Qilive.
