"""Draw charts/cover.png: a week of seven day tiles, with a Thursday release highlighted.

Run from the repo root:  python src/make_cover.py
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

WIDTH_PIXELS = 1600
HEIGHT_PIXELS = 900
DPI = 200

BACKGROUND = "#141414"
TILE_BEFORE_RELEASE = "#2b2b2b"
TILE_AFTER_RELEASE = "#e50914"
TEXT_BEFORE_RELEASE = "#6f6f6f"
TEXT_WHITE = "#ffffff"
TEXT_HEADER = "#8d96a3"
TEXT_SUBLINE = "#a8a8a8"

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
RELEASE_DAY = "THU"

TILE_WIDTH = 148
TILE_HEIGHT = 192
TILE_GAP = 13
TILE_TOP = 309

HEADER_TEXT = "NETFLIX TOP 10  ·  WEEK 1"
MAIN_TEXT = 'A Thursday release gets 4 days in its "week 1".'
SUBLINE_TEXT = "What that does to the public week-1 number."


def points(pixels):
    """Convert a text height in pixels to matplotlib points at this DPI."""
    return pixels * 72 / DPI


def draw_cover(output_path="charts/cover.png"):
    """Draw the cover on a 1600 x 900 pixel canvas and save it."""
    figure = plt.figure(figsize=(WIDTH_PIXELS / DPI, HEIGHT_PIXELS / DPI), dpi=DPI)
    figure.patch.set_facecolor(BACKGROUND)
    # One axis that covers the whole canvas, measured in pixels from the top-left corner.
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set_xlim(0, WIDTH_PIXELS)
    axis.set_ylim(HEIGHT_PIXELS, 0)
    axis.axis("off")

    center_x = WIDTH_PIXELS / 2
    axis.text(
        center_x,
        148,
        HEADER_TEXT,
        color=TEXT_HEADER,
        fontsize=points(35),
        fontweight="bold",
        ha="center",
        va="center",
    )

    row_width = len(DAYS) * TILE_WIDTH + (len(DAYS) - 1) * TILE_GAP
    row_left = (WIDTH_PIXELS - row_width) / 2
    release_index = DAYS.index(RELEASE_DAY)
    for index, day in enumerate(DAYS):
        tile_left = row_left + index * (TILE_WIDTH + TILE_GAP)
        after_release = index >= release_index
        tile = FancyBboxPatch(
            (tile_left, TILE_TOP),
            TILE_WIDTH,
            TILE_HEIGHT,
            boxstyle="round,pad=0,rounding_size=10",
            linewidth=0,
            facecolor=TILE_AFTER_RELEASE if after_release else TILE_BEFORE_RELEASE,
        )
        axis.add_patch(tile)
        axis.text(
            tile_left + TILE_WIDTH / 2,
            TILE_TOP + TILE_HEIGHT / 2,
            day,
            color=TEXT_WHITE if after_release else TEXT_BEFORE_RELEASE,
            fontsize=points(40),
            fontweight="bold",
            ha="center",
            va="center",
        )
        if day == RELEASE_DAY:
            axis.text(
                tile_left + TILE_WIDTH / 2,
                TILE_TOP + TILE_HEIGHT + 34,
                "release",
                color=TILE_AFTER_RELEASE,
                fontsize=points(27),
                ha="center",
                va="center",
            )

    axis.text(
        center_x,
        661,
        MAIN_TEXT,
        color=TEXT_WHITE,
        fontsize=points(54),
        ha="center",
        va="center",
    )
    axis.text(
        center_x,
        766,
        SUBLINE_TEXT,
        color=TEXT_SUBLINE,
        fontsize=points(39),
        ha="center",
        va="center",
    )
    figure.savefig(output_path, dpi=DPI, facecolor=BACKGROUND)
    plt.close(figure)


if __name__ == "__main__":
    draw_cover()
    print("charts/cover.png written")
