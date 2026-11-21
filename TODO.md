# TODO — visu-velo

## À faire (par ordre de priorité)

On en choisit un, puis il est codé jusqu'au bout.

### 1. Fiche parcours (recommandé, dernier gros morceau)
- [ ] `load_profile(gpx_path)` dans `velo_tools/openrunner.py` (gpxpy, distance cumulée) + test.
- [ ] Route `GET /api/routes/<id>` → résumé + profil (404 sinon).
- [ ] Panneau ouvert au clic sur un parcours :
  - profil altimétrique (Chart.js 4.4.1) ;
  - cols positionnés sur le profil ;
  - marqueur sur la carte qui suit le survol du profil.

### 2. Retouches carte (petits objectifs)
- [ ] Exclure les tracés lointains (Montagne Pelée, Martinique, id 18107204) du cadrage initial.
- [ ] Bouton « recentrer » qui efface la vue mémorisée.
- [ ] Recherche par nom / lieu de départ.
- [ ] Mémoriser filtres et tri dans `localStorage`.
- [ ] [2026-11-20] Bouton « vue 3D » sur `/parcours` : garder Leaflet, vue 3D avec MapLibre GL + tuiles AWS Terrain Tiles.
- [ ] [2026-11-20] `download_openrunner.py` : mettre à jour un seul tracé à partir de son id.

### 3. Ménage du dépôt
- [ ] Ajouter `requests` à `requirements.txt` (utilisé par `download_openrunner.py`).
- [x] Section README pour `/parcours` et `download_openrunner.py`.
- [ ] Fichiers qui traînent :
  - CSV et `.ods` à la racine ;
  - `fix_fit.py` (dépend de `fit_tool`, absent de `requirements.txt`) ;
  - `show_colors.py`, `taurize.csv` ;
  - `openrunner_routes.*` non suivis.
- [ ] L'ancienne appli web (`/matplotlib`, `/velo`) lit un `./parcours.csv` qui n'existe plus : à réparer ou supprimer.

### 4. Plus tard : relier parcours et sorties réelles
- [ ] Rapprocher les tracés OpenRunner des sorties enregistrées (FIT/CSV) ou du programme ODS, pour savoir quels parcours ont été réellement roulés et combien de fois.

### 5. Nouvelles idées (2026-11-19)
- [ ] Télécharger les parcours depuis intervals.icu et les afficher dans le web.
- [ ] ods 2 png : ajouter un panneau des temps qui montre les barres en temps (durée), pas en distance.
- [ ] [2026-11-21] Visualiser / analyser les sorties Bryton (sources : Bryton Active, intervals.icu, compteur ; FIT dans `data/bryton-fits/`).

## Décisions

- **Stack** : Flask existant + Leaflet 1.9.4 via cdnjs, sans build front ni plugin.
- **Tracés carte** : polyline `shape.full_encoded` du JSON (décodée en JS), pas les GPX. Les GPX ne servent qu'au profil (leurs `<time>` sont factices).
- **Date d'un parcours** : colonne `date` de `routes.csv` (`dd.mm yyyy`), sinon `created_at` du JSON.
- **Mémoire de vue** : `localStorage` plutôt que cookie (seul le navigateur en a besoin).
- **Couleurs** : une teinte par parcours, calculée depuis l'id (pas d'angle d'or), donc stable quand on filtre ou ajoute des parcours. L'activité se lit au trait : plein pour le vélo de route, pointillés pour le reste.
- **Survol d'une ligne de liste** : seul ce tracé reste visible (zoom inchangé) ; tous reviennent quand la souris quitte la liste.
- **Plages distance / D+** : deux champs numériques min/max, pas de double curseur.
- **Filtres** non mémorisés, pas de recherche texte pour l'instant.
- **D+ manquant** : exclu dès qu'une borne de D+ est saisie ; valeurs manquantes en fin de tri.
- **Tests** : pytest sur fixtures dédiées (`data/` est dans `.gitignore`).
- **Méthode de travail** : on s'accorde sur un objectif, puis on le code de bout en bout.

## Commandes

```bash
# Télécharger / mettre à jour les parcours OpenRunner
workon visu-velo && python download_openrunner.py

# Lancer l'appli (port 5000 déjà pris)
workon visu-velo && flask --app visu_velo_web run --port 5001
# puis http://127.0.0.1:5001/parcours

# Tests et lint
workon visu-velo && python -m pytest tests/ -q
ruff check . && ruff format --check velo_tools tests
```

Relancer le serveur pour voir de nouveaux parcours (cache).
Pour revenir au cadrage complet de la carte : `localStorage.removeItem("parcours.mapView")` dans la console du navigateur.

## Fait (2026-10-16) — carte des parcours OpenRunner

- Branche `fit-analyse` mergée dans `main` (`865553d`).
- `download_openrunner.py` versionné : télécharge GPX + JSON de chaque parcours dans `data/openrunner/` et tient le manifeste `routes.csv`.
- `velo_tools/openrunner.py` :
  - `load_route_summary(json_path, manifest_row)` : lit le JSON d'un parcours et renvoie un résumé ;
  - `load_routes(data_dir)` : tous les parcours, du plus récent au plus ancien ;
  - `read_manifest(data_dir)` : lit `routes.csv`.
- Flask (`web/__init__.py`) :
  - `GET /api/routes` : résumés en JSON, lus une fois par processus (`lru_cache`) ;
  - `GET /parcours` : page carte + liste.
- Page `/parcours` (`web/templates/parcours.html`, `web/static/parcours.{js,css}`) :
  - carte Leaflet des 144 tracés, une couleur par parcours (calculée depuis l'id), vélo de route en trait plein et autres activités en pointillés, avec légende ;
  - survol d'un tracé : il s'épaissit et une info-bulle apparaît ;
  - clic sur un tracé : popup avec nom, km, D+, date, départ, cols et lien OpenRunner ;
  - position et zoom de la carte mémorisés dans le `localStorage` du navigateur ;
  - liste à gauche, triable par nom, date, km et D+ ;
  - filtres : activité, année, type, distance min/max, D+ min/max, « zone visible seulement » ;
  - synchro liste ↔ carte : survol d'une ligne pour n'afficher que son tracé, clic pour zoomer et ouvrir la popup, compteur `n / 144`.
- Tests : `tests/test_openrunner.py`, 5 tests pytest sur les fixtures de `tests/fixtures/openrunner/`.
- Commits :
  - `e6f25c5` : la carte ;
  - `8663f34` : la liste filtrable ;
  - `e80c731` : couleurs par parcours et survol qui isole un tracé.
