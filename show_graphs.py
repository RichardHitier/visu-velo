from os.path import basename, splitext

import matplotlib.pyplot as plt

from velo_tools.graphers import show_resume
from velo_tools.readers import ods_to_df, summarize


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

    if len(sys.argv) < 3:
        my_help("Give all args")

    display_mode = sys.argv[1]
    num_plots = sys.argv[2]

    if display_mode not in ["show", "save"]:
        my_help("First arg should be 'show' or 'save'")

    if num_plots not in ["1", "2"]:
        my_help("Second arg should be '1' or '2'")

    max_files = int(num_plots)
    show_to_screen = display_mode == "show"
    for f in odsfiles[:int(num_plots)]:
        plot_file(f, show_to_screen)
