# Identité Kairos

## Concept

Kairos représente le moment juste : la marque associe une **barre verticale** et un **chevron** pour dessiner un `K`. La barre donne le repère stable, le chevron indique la direction et le mouvement. Leur jonction est marquée par un **point signal ambre**, le déclencheur qui transforme une information en action au bon moment.

Le wordmark `Kairos` est un dessin géométrique spécifique à la marque. Tous les SVG sont écrits à la main et autonomes : lettres et slogan sont des tracés, sans élément `<text>`, police chargée, image matricielle incorporée ni dépendance réseau. Les fichiers de `frontend/public/brand` sont les sources canoniques ; ceux de `frontend/src/assets/brand` sont leurs copies de distribution.

## Palette

| Rôle | Couleur | Hexadécimal | Usage |
| --- | --- | --- | --- |
| Indigo Kairos | Indigo très profond | `#1E1B4B` | Marque sur fond clair, fonds sombres et icônes |
| Point signal | Ambre | `#F59E0B` | Point de jonction et accents signal uniquement |
| Ardoise | Gris bleuté | `#64748B` | Informations secondaires et décor discret |
| Blanc cassé | Clair | `#F8FAFC` | Marque inversée sur indigo |

L’ambre reste réservé au signal : il ne remplace pas l’indigo du `K` ou du wordmark. Sur fond sombre, utiliser le logo inversé blanc cassé avec le point ambre. La version monochrome utilise une seule couleur via `currentColor`, y compris pour le point.

## Variantes et fichiers

- `kairos-mark.svg` : marque seule indigo + ambre, pour fond clair.
- `kairos-mark-mono.svg` : marque seule monochrome, coloriable avec `currentColor`.
- `kairos-wordmark.svg` : wordmark seul en tracés, coloriable avec `currentColor`.
- `kairos-logo.svg` : logo horizontal pour fond **clair**.
- `kairos-logo-dark.svg` : logo horizontal inversé pour fond **sombre**.
- `kairos-logo-mono.svg` : logo horizontal monochrome pour impression ou gravure une couleur.
- `favicon.svg`, `favicon-16.png`, `favicon-32.png` : icône à coins arrondis pour navigateur.
- `apple-touch-icon.svg`, `apple-touch-icon.png` : icône plein cadre 180 × 180 px.
- `icon-192.png`, `icon-512.png` : icônes plein cadre avec zone de sécurité pour les masques système.
- `kairos-mark-512.png` : export haute définition de la marque seule sur transparence.
- `og-image.svg`, `og-image.png` : carte 1200 × 630 px, logo centré sur indigo et slogan « Le bon message, au bon moment. » lettré en capitales vectorielles.

## Zone de protection

Soit **h** la hauteur du point signal ambre, c’est-à-dire son diamètre dans la marque de référence. Laisser une zone libre d’au moins **2 × h de chaque côté** du logo ou de la marque, mesurée depuis leurs limites visibles.

Aucun texte, bord, autre logo ou élément graphique actif ne doit pénétrer dans cette zone. Pour une icône plein cadre, le fond peut continuer, mais le sujet reste dans sa zone de sécurité interne. La zone de protection est un minimum : l’augmenter sur les compositions ouvertes.

## Tailles minimales

| Version | Numérique | Impression |
| --- | --- | --- |
| Marque seule | 24 × 24 px | 8 mm de large |
| Logo horizontal | 120 px de large | 30 mm de large |
| Wordmark seul | 96 px de large | 25 mm de large |
| Favicon | 16 × 16 px, version dédiée uniquement | — |

Sous 120 px de large, ne pas réduire le logo horizontal : utiliser la marque seule. Les exports favicon 16 px et 32 px sont des exceptions conçues pour leur grille d’affichage. Ne pas extrapoler d’autres tailles depuis un PNG ; repartir du SVG.

## Interdits

- Ne pas étirer, comprimer, incliner, faire pivoter ou redessiner la marque.
- Ne pas dissocier, déplacer ou redimensionner la barre, le chevron ou le point.
- Ne pas changer les couleurs canoniques, utiliser un dégradé ou recolorer le point signal indépendamment hors version monochrome.
- Ne pas ajouter d’ombre, lueur, contour, biseau ou autre effet.
- Ne pas placer la version claire sur un fond sombre, ni une version sur un fond sans contraste suffisant ou visuellement chargé.
- Ne pas rogner la marque, couper le slogan de la carte OG ou empiéter sur la zone de protection.
- Ne pas remplacer les tracés du wordmark par du texte ni substituer une police.
- Ne pas utiliser la version couleur quand une seule encre est disponible ; utiliser alors la version monochrome.
- Ne pas agrandir les PNG favicon pour créer des visuels haute définition.

## Construction reproductible

Avec les dépendances racine déjà installées :

```sh
npm run brand
# ou, sans passer par npm :
node scripts/build-brand.mjs
```

Le script contrôle l’autonomie des SVG, synchronise les deux dossiers `brand`, produit les PNG avec `sharp`, vérifie leurs dimensions et copie les mêmes octets dans `public` et `src`. Il ne modifie ni composant, ni manifeste, ni fichier hors des actifs de marque.
