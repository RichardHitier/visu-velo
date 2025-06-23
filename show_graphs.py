import os
from os.path import basename, splitext

import matplotlib.pyplot as plt

from velo_tools.graphers import show_resume, plot_fit
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

    else:
        print("First arg should be in [fit, bike]")
