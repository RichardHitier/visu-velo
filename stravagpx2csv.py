import gpxpy
import pandas as pd
import sys
import os

if len(sys.argv) > 1:
    gpx_filepath = sys.argv[1]
else:
    print("Give gpx file as arg")
    sys.exit()


if os.path.exists(gpx_filepath):
    path, gpx_filename = os.path.split(gpx_filepath)
    gpx_name, extension = os.path.splitext(gpx_filename)
    csv_filename = f"{gpx_name}.csv"
else:
    print(f"No such file {gpx_filename}")
    sys.exit()

if extension != '.gpx':
    print(f"Only gpx file allowed as input")
    sys.exit()
    



# === Read GPX file ===
with open(gpx_filepath, 'r') as gpx_fd:
    gpx = gpxpy.parse(gpx_fd)

data = []
start_time = None

for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            if not start_time:
                start_time = point.time
            heart_rate = None
            if point.extensions:
                for ext in point.extensions:
                    for child in ext:
                        if 'hr' in child.tag.lower():
                            heart_rate = child.text
            data.append({
                'time': point.time,
                'elapsed_time': (point.time - start_time).total_seconds(),
                'latitude': point.latitude,
                'longitude': point.longitude,
                'elevation': point.elevation,
                'heart_rate': heart_rate
            })

# === Save as CSV ===
df = pd.DataFrame(data)
df['heart_rate'] = pd.to_numeric(df['heart_rate'], errors='coerce')  # Conversion en numérique
df.to_csv(csv_filename, index=False)

print(f"✅ Fichier converti et enregistré sous : {csv_filename}")

# vim: tw=0
