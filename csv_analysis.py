
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

# === Chargement du fichier CSV ===
fichier_csv = "20250528PomasMatinal.csv"
df = pd.read_csv(fichier_csv)
df['time'] = pd.to_datetime(df['time'])

# === Paramètres de zones personnalisées ===
zones = {
    "Z1": (0, 130),
    "Z2": (130, 140),
    "Z3": (140, 160),
    "Z4": (160, 999)  # tout ce qui dépasse
}

def zone_cardiaque(fc):
    for zone, (min_fc, max_fc) in zones.items():
        if min_fc <= fc < max_fc:
            return zone
    return None

# === Tracé fréquence cardiaque + altitude ===
fig, ax1 = plt.subplots(figsize=(14, 6))
color = 'tab:red'
ax1.set_xlabel('Temps')
ax1.set_ylabel('Fréquence cardiaque (bpm)', color=color)
ax1.plot(df['time'], df['heart_rate'], color=color, label="FC")
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('Altitude (m)', color=color)
ax2.plot(df['time'], df['elevation'], color=color, linestyle='--', label="Altitude")
ax2.tick_params(axis='y', labelcolor=color)

plt.title("Profil fréquence cardiaque et altitude")
plt.tight_layout()
plt.grid()
plt.show()

# === Détection des bosses par dénivelé cumulé ===
df['elevation_diff'] = df['elevation'].diff().fillna(0)
df['climbing'] = df['elevation_diff'] > 0.2  # pente positive significative
df['climb_block'] = (df['climbing'] != df['climbing'].shift()).cumsum()

bosses = []
for _, group in df.groupby('climb_block'):
    if group['climbing'].iloc[0] and group['elevation'].max() - group['elevation'].min() > 4:
        bosses.append(group)

print(f"✅ {len(bosses)} bosses détectées.")

# === Analyse de chaque bosse ===
for i, bosse in enumerate(bosses, 1):
    t_start = bosse['time'].iloc[0]
    t_end = bosse['time'].iloc[-1]
    fc_moy = bosse['heart_rate'].mean()
    zc = zone_cardiaque(fc_moy)
    d_plus = bosse['elevation'].max() - bosse['elevation'].min()
    print(f"\nBosse {i} :")
    print(f"  ➤ Durée : {t_end - t_start}")
    print(f"  ➤ Dénivelé : {d_plus:.1f} m")
    print(f"  ➤ FC moyenne : {fc_moy:.1f} bpm ({zc})")

