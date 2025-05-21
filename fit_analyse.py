
import os
import pandas as pd
from fitparse import FitFile
import matplotlib.pyplot as plt

def extraire_hr(file_path):
    fitfile = FitFile(file_path)
    data = []

    for record in fitfile.get_messages("record"):
        record_data = {field.name: field.value for field in record}
        if "timestamp" in record_data and "heart_rate" in record_data:
            data.append(record_data)

    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df

def detect_effort_soutenu(df, window_min=20):
    """Détecte la période de 20 minutes avec la plus haute FC moyenne."""
    window = window_min * 60  # en secondes
    df = df.copy()
    df = df.resample("1S").mean().interpolate()
    rolling_avg = df["heart_rate"].rolling(window=window, min_periods=window).mean()
    max_avg = rolling_avg.max()
    start_time = rolling_avg.idxmax()
    end_time = start_time + pd.Timedelta(seconds=window)
    return max_avg, start_time, end_time

def analyser_fichiers(dossier_fit):
    resultats = []
    for nom_fichier in os.listdir(dossier_fit):
        if nom_fichier.endswith(".fit"):
            chemin = os.path.join(dossier_fit, nom_fichier)
            try:
                df = extraire_hr(chemin)
                lthr, debut, fin = detect_effort_soutenu(df)
                resultats.append({
                    "fichier": nom_fichier,
                    "LTHR estimée": round(lthr),
                    "début effort": debut,
                    "fin effort": fin,
                    "FC max": df["heart_rate"].max()
                })
                print(f"{nom_fichier} : LTHR estimée = {round(lthr)} bpm")
            except Exception as e:
                print(f"Erreur sur {nom_fichier} : {e}")
    return pd.DataFrame(resultats)

# Exemple d’utilisation
if __name__ == "__main__":
    dossier = "data/decathlon_fits/"  # Remplace par le chemin de ton dossier
    df_resultats = analyser_fichiers(dossier)
    print("\nRésumé :")
    print(df_resultats)

