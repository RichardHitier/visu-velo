# visu-velo

Quatre usages principaux :

| Je veux…                       | Commande                                                      |
|--------------------------------|---------------------------------------------------------------|
| ods 2 PNG                      | `python show_graphs.py plot ProgrammeCyclo_25-26.ods`         |
| intervals.ico 2 ods            | `python download_intervals.py ProgrammeCyclo_26-27.ods`       |
| view opennrunner  trajectories | `gunicorn visu_velo_web:app` → http://127.0.0.1:8000/parcours |
| km des 52 dernières semaines   | `python show_graphs.py weeks`                                 |

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

### Ancienne saison sans Journal (22-23)

    python historique_to_journal.py /home/richard/03COMMON/0000velo/ProgrammeCyclo_22-23.ods --dry-run
    python historique_to_journal.py /home/richard/03COMMON/0000velo/ProgrammeCyclo_22-23.ods

Ajoute une feuille Journal remplie depuis la feuille Historique (sorties vélo seulement ; `type` et `zone` vides, RPE, FC max et V max en commentaire). Une copie `.bak` est faite avant. Refuse si le Journal existe déjà.

## 3. Carte des parcours

    python download_openrunner.py --activity   # JSON manquants → data/openrunner/<id>.json
    python download_openrunner.py              # GPX manquants  → data/openrunner/<id>.gpx
    gunicorn visu_velo_web:app                 # puis http://127.0.0.1:8000/parcours

La carte lit uniquement les JSON : tracé, km, D+ et cols. Les GPX ne servent que de sauvegarde. Les fichiers déjà présents ne sont pas retéléchargés.

### Un parcours a changé sur OpenRunner

    python download_openrunner.py --activity --force

1. `--force` retélécharge tous les JSON (environ 1 min pour 144 parcours ; pas d'option pour un seul).
2. Relancer gunicorn : les parcours sont gardés en cache.

Pour un nouveau parcours, l'ajouter d'abord à `openrunner_routes.json` : le script lit cette liste mais ne la crée pas.

Le serveur propose aussi `/matplotlib` (le PNG de la saison) et `/velo` (le graphique Bokeh).

## 4. Km des 52 dernières semaines

    export INTERVALS_API_KEY=...  INTERVALS_ATHLETE_ID=...
    python show_graphs.py weeks        # → semaines_AAAA-MM-JJ.png
    python show_graphs.py weeks show   # affiche au lieu d'enregistrer

Une grille de 4 × 13 carrés, un par semaine (du lundi au dimanche), jusqu'à la semaine en cours incluse. La couleur va du bleu clair au bleu foncé selon les km ; une semaine sans sortie est grise. Les km viennent directement d'intervals.icu (sorties vélo uniquement), pas des ODS.
