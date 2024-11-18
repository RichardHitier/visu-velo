import pandas as pd
import datetime


def ods_to_df(file_path):
    my_df = pd.read_excel(file_path, sheet_name="Journal", header=4, index_col=3,
                          parse_dates=True)
    pd.set_option('expand_frame_repr', False)
    pd.set_option('display.max_rows', None)

    my_df.drop(my_df.columns[[0, 1, 2, 3, 8, 10, 11, 12, 13, 14, 15, 16, 17]], axis=1, inplace=True)
    my_df.dropna(inplace=True)
    my_df.index = pd.to_datetime(my_df.index)

    one_week_before = my_df.index[0] - datetime.timedelta(weeks=1)
    one_week_after = my_df.index[-1] + datetime.timedelta(weeks=1)

    alldays_idx = pd.date_range(start=one_week_before, end=my_df.index[-1], freq='D')
    df_reindexed = my_df.reindex(alldays_idx)

    return df_reindexed


def summarize(my_df):
    """
    From a dataframe with dates and kilometers,
    insert a new column with km sum by week
    """


    # Insert two new columns: week and month (with year)
    my_df["week"] = pd.to_datetime(my_df.index).strftime('%Y-%W')
    # my_df["month"] =  pd.to_datetime(my_df.index).strftime('%Y-%m')

    week_sum = my_df.groupby('week').agg({"km": "sum"})

    week_sum.set_index(pd.to_datetime(week_sum.index + '1', format="%Y-%W%w"), inplace=True)
    week_sum['mondays'] = week_sum.index.strftime("%a %d/%m")

    my_df["date_as_str"] = my_df.index.strftime("%Y-%m-%d-%a")

    my_df["week_sum"] = week_sum["km"]
    return my_df

