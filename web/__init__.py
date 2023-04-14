import datetime
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, render_template
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.models import HoverTool, ColumnDataSource


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        time = datetime.datetime.now()
        return f"Hello user at {time}"

    @app.route("/matplotlib")
    def velo():
        fichier = "./parcours.csv"
        df = pd.read_csv(fichier, sep=";")
        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        x1 = df["date"]
        y1 = df["km"]
        y2 = df["Deniv"]

        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()

        ax2.plot(x1, y2, "g-")
        ax2.set_ylabel("Dénivelé (m)", color="g")

        ax1.bar(x1, y1, width=0.5)
        ax1.set_ylabel("Km parcourus", color="b")

        plt.xlabel("Date")
        ax1.grid(
            color="#95a5a6", linestyle="--", linewidth=1, axis="y", alpha=0.7
        )

        # ax1.set_xticklabels(df['date'],rotation=90)
        fig.autofmt_xdate()

        png_image = io.BytesIO()
        fig.savefig(png_image, format="png")
        png_image.seek(0)

        png64 = base64.b64encode(png_image.read()).decode("ascii")

        return render_template("velo.html", image=png64)

    @app.route("/velo")
    def bokeh_plot():
        fichier = "parcours.csv"
        df = pd.read_csv(fichier, sep=";")

        df["date"] = pd.to_datetime(df["date"], dayfirst=True)

        src1 = ColumnDataSource(df)
        src2 = ColumnDataSource(df)
        src3 = ColumnDataSource(df)

        p1 = figure(
            title="Distance parcourue",
            x_axis_label="Date",
            y_axis_label="Distance",
            x_axis_type="datetime",
            sizing_mode="stretch_width",
            height=250,
        )

        p2 = figure(
            title="Dénivelé parcourue",
            x_axis_label="Date",
            y_axis_label="Dénivelé",
            x_axis_type="datetime",
            height=250,
        )

        p1.vbar(
            x="date",
            top="km",
            source=src1,
            legend_label="Distance parcourue (Kilomètre)",
            color="blue",
            bottom=0,
            width=1,
        )
        p2.line(
            "date",
            "Deniv",
            name="hov",
            source=src2,
            legend_label="Dénivelé (Mètre)",
            color="green",
        )
        p2.circle("date", "Deniv", source=src3, size=8, color="darkgreen")

        hover_tool1 = HoverTool(
            tooltips=[("Date", "@date{%F}"), ("Distance", "@km")],
            formatters={"@date": "datetime"},
        )

        hover_tool2 = HoverTool(
            tooltips=[("Date", "@date{%F}"), ("Dénivelé", "@Deniv")],
            formatters={"@date": "datetime"},
            name="hov",
        )

        p1.add_tools(hover_tool1)
        p2.add_tools(hover_tool2)
        p2.toolbar.logo = None

        script1, div1 = components(p1)
        script2, div2 = components(p2)

        return render_template(
            "bokeh_plot.html",
            script=[script1, script2],
            div=[div1, div2],
            js_resources=INLINE.render_js(),
            css_resources=INLINE.render_css(),
        ).encode(encoding="UTF-8")

    @app.route("/chartjs")
    def chartjs():
        fichier = "parcours.csv"
        df = pd.read_csv(fichier, sep=";")

        df["date"] = pd.to_datetime(df["date"], dayfirst=True)
        dates = df["date"].tolist()
        deniv = df["Deniv"].tolist()
        km = df["km"].tolist()
        print(df["date"])
        return render_template("chartjs.html", dates=dates, deniv=deniv, km=km)

    return app
