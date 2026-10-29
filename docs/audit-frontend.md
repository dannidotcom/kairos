# Audit frontend Kairos

## Conservé

- Les routes React sous `/app/*` et les routes publiques `/`, `/login`, `/mentions-legales`, `/privacy`, `/terms`.
- Le client TanStack Query, l'authentification, les contrats API existants et les types TypeScript.
- Les écrans et flux métier actuellement implémentés : tableau de bord, leads, signaux, campagnes, ICP, Unibox, paramètres, connexion, invitation et identité visuelle.
- Le composant de logo, l'identité Kairos, les traductions FR/EN existantes et le mode de démonstration.

## Remplacé

- La présentation du shell applicatif sera migrée vers des composants de design system et des tokens CSS communs.
- Les couleurs, rayons, ombres, polices et états visuels seront centralisés et non dupliqués dans les écrans.
- Les composants applicatifs génériques seront progressivement remplacés par des primitives accessibles (dialogues, menus, infobulles, onglets, palette de commandes).
- La page de connexion, l'interface `/app` et les écrans métier recevront une passe d'alignement, d'accessibilité et d'états chargement/erreur/vide.

## Architecture de migration

- `src/design-system/` : tokens, primitives, hooks visuels et catalogue de composants.
- `src/features/` : requêtes et composants métier lorsque les écrans seront découpés par domaine.
- `src/pages/` : composition des routes, sans duplication de logique visuelle.
- `src/landing/` : sections de la landing page et scènes animées.
- `src/lib/` : API, authentification, i18n et utilitaires conservés.

## Contraintes vérifiées

- Aucun contrat HTTP ou format de réponse API n'est modifié par la refonte visuelle.
- Les animations non essentielles sont désactivées pour `prefers-reduced-motion`.
- L'application conserve le défilement natif ; Lenis reste limité à la landing page.
- Les données LinkedIn restent fictives ou issues de l'API réelle; aucune statistique de démonstration n'est présentée comme un résultat produit.
