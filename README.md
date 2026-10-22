# Anime-Sama TV — Qilive / NuvioTV

Connecteur expérimental dédié **uniquement à Anime-Sama** pour NuvioTV Android TV.

## Origine et licence
Basé sur [Gowaru/gowaru-nuvio-providers](https://github.com/Gowaru/gowaru-nuvio-providers), sous licence **GPL-3.0**. Le code source complet, les dépendances et le bundle généré sont conservés dans ce dépôt.

## Correctif 1.1.59 (22 octobre 2026)
Sur la Qilive Android TV 11, `episodes.js` répondait HTTP 403 avec le connecteur 1.1.58, alors que la page catalogue était accessible. La fonction `fetchJs()` dans `src/anime-sama/extractor.js` ne fournissait pas le `Referer` de la page de lecture. La correction ajoute ce contexte aux requêtes des listes d'épisodes.

## Installation
NuvioTV > Paramètres > Contenu et découverte > Plugins > Ajouter un dépôt :

```
https://raw.githubusercontent.com/JoeSm0ke/Nuvio-AnimeSama-Qilive/main/manifest.json
```

Le manifeste active un seul fournisseur : **Anime-Sama (Qilive)**. Désactiver le fournisseur Anime-Sama de Gowaru pour éviter un doublon.

## Construction
```bash
npm ci
node build.js anime-sama
```

## Validation
Testé sur Qilive UHD Android TV 11 (ARMv7) avec NuvioTV 1.0.0 : Jujutsu Kaisen S1E1, VF et VOSTFR, quatre flux retournés, lecture vidéo démarrée. Le site et les hébergeurs tiers peuvent changer et interrompre le fonctionnement.

Ce dépôt ne contient ni médias, ni vidéos, ni fichiers téléchargés depuis les hébergeurs. Il ne fournit aucune licence sur les œuvres diffusées par les sites tiers.

## Accueil Anime-Sama (catalogue Stremio/Nuvio séparé)

L'interface Nuvio utilise les catalogues **Stremio**, indépendamment des plugins de flux. Le catalogue Anime-Sama est servi statiquement par GitHub Pages, avec deux sections : derniers ajouts et sorties récentes.

Adresse à installer dans **Nuvio > Addons** :
```
https://joesm0ke.github.io/Nuvio-AnimeSama-Qilive/manifest.json
```

Les affiches sont récupérées depuis Anime-Sama. Les identifiants IMDb proviennent de la recherche Cinemeta avec correspondance stricte, pour que le lecteur Nuvio récupère les saisons et les épisodes associés. Les titres sans correspondance fiable sont ignorés : ce catalogue est une **sélection indexée**, pas encore l'intégralité du site. Le plugin de flux Anime-Sama (Qilive) reste nécessaire.

Pour reconstruire le catalogue :
```sh
pip install requests beautifulsoup4 rapidfuzz
python scripts/build_catalog.py
```

Une action GitHub permet une mise à jour programmée deux fois par semaine. Elle ne télécharge ni vidéo ni épisode.
