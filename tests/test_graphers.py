from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")

from matplotlib.patches import Rectangle  # noqa: E402

from velo_tools.graphers import plot_weekly_grid  # noqa: E402


def test_plot_weekly_grid_draws_one_square_per_week():
    first = date(2025, 11, 24)
    weeks = [(first + timedelta(weeks=n), n % 5 * 20) for n in range(52)]
    fig = plot_weekly_grid(weeks)
    ax = fig.axes[0]
    squares = [p for p in ax.patches if isinstance(p, Rectangle)]
    assert len(squares) == 52
    total = sum(km for _, km in weeks)
    assert f"{total} km sur 52 semaines" in ax.get_title()
    assert len(ax.get_yticklabels()) == 4
