
import gpxpy

# Chemins vers les fichiers à fusionner
fichier1 = 'data/20250503_Malepere-1.gpx'
fichier2 = 'data/20250503_Malepere-2.gpx'
fichier_sortie = 'data/20250503_Malepere.gpx'

# Charger les deux fichiers GPX
with open(fichier1, 'r') as f1, open(fichier2, 'r') as f2:
    gpx1 = gpxpy.parse(f1)
    gpx2 = gpxpy.parse(f2)

# Ajouter les traces du deuxième fichier au premier
for track in gpx2.tracks:
    gpx1.tracks.append(track)

# Écrire le fichier fusionné
with open(fichier_sortie, 'w') as f_out:
    f_out.write(gpx1.to_xml())

print(f"Fichier fusionné écrit dans {fichier_sortie}")

