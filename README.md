# visu-velo

Trois usages principaux :

| Je veux…                       | Commande                                                      |
|--------------------------------|---------------------------------------------------------------|
| ods 2 PNG                      | `python show_graphs.py plot ProgrammeCyclo_25-26.ods`         |
| intervals.ico 2 ods            | `python download_intervals.py ProgrammeCyclo_26-27.ods`       |
| view opennrunner  trajectories | `gunicorn visu_velo_web:app` → http://127.0.0.1:8000/parcours |

Toujours activer l'env avant : `workon visu-velo`.

## 1. PNG de la saison

    python show_graphs.py plot ProgrammeCyclo_25-26.ods        # → ProgrammeCyclo_25-26.png
    python show_graphs.py plot ProgrammeCyclo_25-26.ods show   # affiche au lieu d'enregistrer

Le PNG est écrit dans le dossier courant. Il contient trois graphiques : le D+, les km par jour colorés par zone, et les km par semaine avec le cumul.

## 2. Remplir l'ODS depuis intervals.icu

    export INTERVALS_API_KEY=...  INTERVALS_ATHLETE_ID=...
    python download_intervals.py ProgrammeCyclo_26-27.ods --dry-run         # liste sans écrire
    python download_intervals.py ProgrammeCyclo_26-27.ods                   # écrit dans le fichier
    python download_intervals.py ProgrammeCyclo_26-27.ods --output OUT.ods  # écrit ailleurs

La saison vient du nom du fichier (26-27, donc du 01/11/2026 au 31/10/2027). Seules les dates absentes du Journal sont ajoutées. `type`, `zone` et le commentaire restent à remplir à la main.

## 3. Carte des parcours

    python download_openrunner.py   # met à jour data/openrunner/ (GPX + JSON)
    gunicorn visu_velo_web:app      # puis http://127.0.0.1:8000/parcours

Le serveur propose aussi `/matplotlib` (le PNG de la saison) et `/velo` (le graphique Bokeh).
