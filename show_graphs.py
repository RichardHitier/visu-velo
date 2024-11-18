
import matplotlib.pyplot as plt

from velo_tools.graphers import show_resume
from velo_tools.readers import ods_to_df, summarize

# my_odsfile_path = "/home/richard/03COMMON/0000velo/ProgrammeCyclo_23-24.ods"
my_odsfile_path = "/home/richard/03COMMON/0000velo/ProgrammeCyclo_24-25.ods"

my_df = ods_to_df(my_odsfile_path)

my_df = summarize(my_df)

show_resume(my_df)
# print(my_df)


# plt.show()