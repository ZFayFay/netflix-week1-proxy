"""Shared chart style, so every figure in the notebook looks the same."""

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# One color carries the measured data. Gray carries the reference it is compared with.
ACCENT = "#2a78d6"
ACCENT_LIGHT = "#cde2fb"
REFERENCE = "#9a9994"
INK = "#1f1f1e"
MUTED = "#6b6a66"
GRID = "#e6e5e1"

SOURCE_LINE = "Data: Netflix Top 10 and What We Watched"
DPI = 200


def apply_chart_style():
    """Set quiet defaults: light grid, no top or right border, dark gray text."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK,
            "ytick.labelcolor": INK,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": False,
            "legend.fontsize": 9,
        }
    )


def views_label(value, position=None):
    """Write an axis value in plain units: 500K, 1M, 10M, 100M."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    return f"{value / 1_000:g}K"


def no_label(value, position=None):
    """Leave the small tick marks between 1M and 10M without text."""
    return ""


def use_views_axis(axis):
    """Label a log axis of views as 1M, 10M, 100M."""
    axis.set_major_formatter(FuncFormatter(views_label))
    axis.set_minor_formatter(FuncFormatter(no_label))


def finish_chart(figure, file_name, note=None):
    """Add the source line (and an optional note above it), then save to charts/."""
    figure.tight_layout()
    # Leave a fixed strip in inches at the bottom for the note and the source line.
    height = figure.get_figheight()
    strip = (0.22 if note is None else 0.4) / height
    figure.subplots_adjust(bottom=figure.subplotpars.bottom + strip)
    if note is not None:
        figure.text(0.012, 0.2 / height, note, fontsize=7.5, color=MUTED, ha="left", va="bottom")
    figure.text(0.012, 0.04 / height, SOURCE_LINE, fontsize=7, color=MUTED, ha="left", va="bottom")
    figure.savefig(f"charts/{file_name}", dpi=DPI)
