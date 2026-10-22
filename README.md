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
