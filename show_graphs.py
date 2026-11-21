import os
import sys
from datetime import date, timedelta
from os.path import basename, splitext

import matplotlib.pyplot as plt

from velo_tools.graphers import show_resume, plot_fit, plot_weekly_grid
from velo_tools.intervals import fetch_activities, rides_to_rows, weekly_km
from velo_tools.readers import ods_to_df, summarize, fit_to_df


def print_file(filename):
    my_df = ods_to_df(filename)
    from pprint import pprint
    pprint(my_df)


def plot_file(filename, _show_to_screen=False):
    my_df = ods_to_df(filename)

    summarized_df = summarize(my_df)

    fig = show_resume(summarized_df)

    root_filename = splitext(basename(filename))[0]
    image_filename = root_filename + ".png"

    if _show_to_screen:
        plt.show()
    else:
        fig.savefig(image_filename)
        print(f"Saved figure into {image_filename}")


def plot_weeks(_show_to_screen=False, weeks=52):
    """PNG of km per week over the last `weeks` weeks, from intervals.icu."""
    try:
        api_key = os.environ["INTERVALS_API_KEY"]
        athlete_id = os.environ["INTERVALS_ATHLETE_ID"]
    except KeyError as missing:
        sys.exit(f"Missing environment variable {missing}")

    today = date.today()
    last_monday = today - timedelta(days=today.weekday())
    first_monday = last_monday - timedelta(weeks=weeks - 1)
    activities = fetch_activities(athlete_id, api_key, first_monday, today)
    weeks_km = weekly_km(rides_to_rows(activities), last_monday, weeks)
    fig = plot_weekly_grid(weeks_km)

    if _show_to_screen:
        plt.show()
    else:
        image_filename = f"semaines_{today.isoformat()}.png"
        fig.savefig(image_filename, dpi=120)
        print(f"Saved figure into {image_filename}")


if __name__ == "__main__":
    import sys


    def my_help(msg):
        print(msg)
        sys.exit(0)


    odsfiles = ["/home/richard/03COMMON/0000velo/ProgrammeCyclo_24-25.ods",
                "/home/richard/03COMMON/0000velo/ProgrammeCyclo_23-24.ods"]

    if len(sys.argv) < 2:
        my_help("Give at least 2 args")

    data_type = sys.argv[1]

    if data_type == 'fit':
        _fit_df = fit_to_df(sys.argv[2])
        fig = plot_fit(_fit_df)
        plt.show()
        print(f"Saved fot fit.png")
    elif data_type == 'print':
        if len(sys.argv) != 3:
            my_help("Give filepath as arg")
        file = sys.argv[2]
        if not os.path.isfile(file):
            my_help(f"{file} doesnt exist")
        print_file(file)
    elif data_type == 'bike':
        display_mode = sys.argv[2]
        num_plots = sys.argv[3]
        if display_mode not in ["show", "save"]:
            my_help("First arg should be 'show' or 'save'")

        if num_plots not in ["1", "2"]:
            my_help("Second arg should be '1' or '2'")

        max_files = int(num_plots)
        show_to_screen = display_mode == "show"
        for f in odsfiles[:int(num_plots)]:
            plot_file(f, show_to_screen)

    elif data_type == 'plot':
        if len(sys.argv) < 3:
            my_help("Usage: show_graphs.py plot <file.ods> [show]")
        file = sys.argv[2]
        if not os.path.isfile(file):
            my_help(f"{file} doesn't exist")
        show_to_screen = len(sys.argv) >= 4 and sys.argv[3] == 'show'
        plot_file(file, show_to_screen)

    elif data_type == 'weeks':
        plot_weeks(len(sys.argv) >= 3 and sys.argv[2] == 'show')

    else:
        print("First arg should be in [fit, bike, plot, print, weeks]")
