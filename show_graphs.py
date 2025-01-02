from os.path import basename, splitext

import matplotlib.pyplot as plt

from velo_tools.graphers import show_resume
from velo_tools.readers import ods_to_df, summarize

odsfiles = ["/home/richard/03COMMON/0000velo/ProgrammeCyclo_24-25.ods",
            "/home/richard/03COMMON/0000velo/ProgrammeCyclo_23-24.ods"]


def plot_file(filename):
    my_df = ods_to_df(filename)

    summarized_df = summarize(my_df)

    fig = show_resume(summarized_df)

    root_filename = splitext(basename(filename))[0]
    image_filename = root_filename + ".png"

    fig.savefig(image_filename)
    print(f"Saved figure into {image_filename}")


for f in odsfiles:
    plot_file(f)
