import datetime
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        time = datetime.datetime.now()
        return f"Hello user at {time}"

    @app.route('/velo')
    def velo():
        fichier = './parcours.csv'
        df = pd.read_csv(fichier, sep=';')
        df['date'] = pd.to_datetime(df['date'], dayfirst=True)
        x1 = df['date']
        y1 = df['km']
        y2 = df['Deniv']

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()

        ax2.plot(x1, y2, 'g-')
        ax2.set_ylabel('Dénivelé (m)', color='g')

        ax1.bar(x1, y1, width=0.5)
        ax1.set_ylabel('Km parcourus', color='b')

        plt.xlabel('Date')
        ax1.grid(color='#95a5a6', linestyle='--', linewidth=1, axis='y', alpha=0.7)

        # ax1.set_xticklabels(df['date'],rotation=90)
        fig.autofmt_xdate()

        png_image = io.BytesIO()
        fig.savefig(png_image, format='png')
        png_image.seek(0)

        png64 = base64.b64encode(png_image.read()).decode('ascii')

        return render_template('velo.html', image=png64)

    return app
