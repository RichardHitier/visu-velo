import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale


def plot_fit(fit_df):
    fig, ax1 = plt.subplots(1, figsize=(20, 8), sharex=True)
    # ax1.plot(fit_df.index, fit_df.steps)
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    ax2.plot(fit_df.index, fit_df.bike_duration, color='red')
    ax2.plot(fit_df.index, fit_df.walking_duration, color='blue')
    ax2.plot(fit_df.index, fit_df.running_duration, color='green')
    return fig


def show_resume(my_df):
    km_df = my_df['km']
    moy_df = my_df['moy']
    type_df = my_df['type']
    elev_df = my_df['elev']
    kmsum_df = my_df['week_sum']

    # print(type_df)
    num_plots = 3

    locale.setlocale(locale.LC_TIME, 'fr_FR.utf8')

    label_fontsize = 18
    bar_color = "black"
    moy_color = "red"
    type_colors = {"foncier": "#fff5ce",
                   "conso": "#ffd428",
                   "recup": "#b4c7dc",
                   "hiit": "#f10d0c",
                   "spec": "#afd095",
                   "deniv": "#ff972f",
                   "tempo": "#cc7a25",
                   "puissance": "#cc7a25",
                   "force": "#b80a09",
                   "course": "#009900"}

    monday_idx = pd.date_range(start=km_df.index[0], end=km_df.index[-1], freq=pd.offsets.Week(weekday=0))

    fig, ax = plt.subplots(num_plots, figsize=(20, 8), sharex=True)

    # Show Elevation
    elev_color = 'tab:green'
    ax0 = ax[0]
    ax0.set_ylim([-39, 1500])
    ax0.set_title("Dénivelé / sortie", y=1.0, pad=16)
    ax0.title.set_size(15)
    ax0.set_ylabel("D+ (m)", color=elev_color, fontsize=label_fontsize, loc="top")
    ax0.tick_params(axis='y', labelcolor=elev_color, labelsize=label_fontsize - 5)
    ax0.yaxis.tick_right()
    ax0.yaxis.set_label_position("right")

    for _hl in [0, 400, 800, 1200]:
        ax0.text(elev_df.index[0], _hl + 0.2, f"{_hl} m", color=elev_color, fontsize=12, horizontalalignment="right")
        ax0.axhline(_hl, color=elev_color, lw=0.8, alpha=1, linestyle='--')

        # ax0.set_ylim([-4000, 1000])
    ax0.plot(elev_df.index, elev_df.interpolate(method="pchip", order=5), color=elev_color)
    ax0.scatter(elev_df.index, elev_df, marker="*", zorder=3, color="red", edgecolor="black", lw=0.5, s=120)
    # show start of weeks
    for monday in monday_idx:
        ax0.axvline(monday, color='black', lw=0.5, alpha=0.5, linestyle='-')

    # ax0.set_ylim([0, 1000])

    ax1 = ax[1]

    ax1.set_title("Distance et Vitesse / sortie", y=1.0, pad=16)
    ax1.title.set_size(15)
    ax1.set_ylim([0, 130])

    # ax1.set_xlabel("Lundis", fontsize=label_fontsize, labelpad=5.0, loc="left")

    # Different bar color depending on block type

    # 1- fill in NaN type
    type_df.fillna("inconnu", inplace=True)
    default_color = '#88e788'

    # 2- then apply color logic
    colors = type_df.map(lambda x: type_colors.get(x, default_color))

    # 3- draw km bars
    ax1.bar(km_df.index, km_df, color=colors, width=0.9, edgecolor="black", linewidth=0.5)

    ax1.set_ylabel("Distance (km)", color=bar_color, fontsize=label_fontsize, loc="bottom")
    ax1.tick_params(axis='y', labelcolor=bar_color, labelsize=label_fontsize - 5)

    # Show start of weeks as V-line
    for monday in monday_idx:
        ax1.axvline(monday, color='black', lw=0.5, alpha=0.5, linestyle='-')

    # Show mean speed as a red spline line with stars for each value
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    ax2.set_ylim([5, 30])
    color = 'tab:red'
    for _hl in [20, 25]:
        ax2.text(moy_df.index[0], _hl + 0.2, f"{_hl} km/h", color=color, fontsize=12, horizontalalignment="right")
        ax2.axhline(_hl, color=color, lw=0.8, alpha=1, linestyle='--')

    ax2.set_ylabel('V. moy. (km/h)', color=color, fontsize=label_fontsize,
                   loc="top")  # we already handled the x-label with ax1
    ## Spline 3
    ax2.plot(moy_df.index, moy_df.interpolate(method="spline", order=3), color="red", lw=2, zorder=-4)
    ## Claude Cubic
    # ax2.plot(moy_df.index, moy_df.interpolate(method="cubic"), color="red", lw=2, zorder=-4)
    ## Claude PCHip
    # from scipy import interpolate
    # f = interpolate.PchipInterpolator(moy_df.dropna().index, moy_df.dropna())
    # ax2.plot(moy_df.index, f(moy_df.index), color="red", lw=2, zorder=-4)
    ## Claude polynomial
    # ax2.plot(moy_df.index, moy_df.interpolate(method="polynomial", order=2), color="red", lw=2, zorder=-4)

    ax2.scatter(moy_df.index, moy_df, marker="*", zorder=3, color="lightgreen", edgecolor="black", lw=0.5, s=120)
    ax2.tick_params(axis='y', labelcolor=color, labelsize=label_fontsize - 5)

    ax3 = ax[2]

    ax3.set_title("Somme distance / semaine (km)", y=1.0, pad=16)
    ax3.title.set_size(15)

    bar_container = ax3.bar(kmsum_df.index, kmsum_df, color='#1455C5', align='edge', width=2, zorder=2,
                            edgecolor="black")

    kmsum_labels = [f"{int(v)}" if pd.notna(v) else "" for v in kmsum_df]
    ax3.bar_label(bar_container, labels=kmsum_labels, label_type="edge", padding=10, zorder=8, color="black",
                  fontsize=15)
    # show start of weeks
    for monday in monday_idx:
        ax3.axvline(monday, color='black', lw=0.5, alpha=0.5, linestyle='-')

    ax3.set_ylim([0, 180])

    # Set x ticks
    # date_format = '%d %b'
    #    https://stackoverflow.com/questions/65469640/major-tick-every-month-and-minor-tick-every-week-in-matplotlib
    # ax3.tick_params(axis='x', labelsize=label_fontsize-5, rotation=30)
    date_format = '%d'
    ax3.tick_params(axis='x', labelsize=label_fontsize - 5)
    # ax3.xaxis.set_minor_formatter(mdates.DateFormatter(date_format))
    # ax3.set_xticks(monday_idx)
    # ax3.set_xticklabels (ax3.get_xticklabels(), ha="right")
    ax3.set_ylabel("Distance (km)", color=bar_color, fontsize=label_fontsize, loc="bottom")
    months = mdates.MonthLocator(interval=1, bymonthday=15)
    months_fmt = mdates.DateFormatter('%b')
    ax3.xaxis.set_major_locator(months)
    ax3.xaxis.set_major_formatter(months_fmt, )
    days = mdates.WeekdayLocator(byweekday=0)
    ax3.xaxis.set_minor_locator(days)
    # ax3.xaxis.set_minor_formatter(ticker.FixedFormatter(ww.Week))
    ax3.xaxis.set_minor_formatter(mdates.DateFormatter("%d"))
    ax3.tick_params(axis='x', which='major', length=1.1, pad=30)
    fig.tight_layout()  # otherwise the right y-label is slightly clipped

    return fig
