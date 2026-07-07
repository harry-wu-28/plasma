"""Shared matplotlib style for Entity analysis plots.

Categorical species colors are fixed by species identity (never re-ranked
when a species is absent). Palette validated 2026-07-07 (CVD worst adjacent
dE 24.2; aqua/yellow are sub-3:1 contrast on the light surface, so every
figure ships a legend and direct labels as relief).
"""

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# species (1-based, this repo's convention) -> categorical slot
SPECIES_COLOR = {
    1: "#2a78d6",  # e-_p    blue
    2: "#1baf7a",  # e+_p    aqua
    3: "#eda100",  # phot    yellow
    4: "#008300",  # e-_sec  green
    5: "#4a3aa7",  # e+_sec  violet
}

# ordinal ramp for "epochs" (time-ordered lines within one panel);
# light-mode ordinal steps start no lighter than step 250
EPOCH_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]

# sequential colormap (magnitude: density maps), blue light->dark,
# near-zero recedes toward the surface
SEQ_CMAP = LinearSegmentedColormap.from_list(
    "ent_seq",
    [SURFACE, "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
     "#256abf", "#184f95", "#0d366b"],
)

# diverging colormap (signed fields), blue <-> red, neutral gray midpoint
DIV_CMAP = LinearSegmentedColormap.from_list(
    "ent_div",
    ["#0d366b", "#2a78d6", "#86b6ef", "#f0efec", "#f0a4a3", "#e34948", "#7c1f1f"],
)


def epoch_colors(n):
    """n time-ordered colors from the ordinal ramp (earliest = lightest)."""
    if n <= 1:
        return [EPOCH_RAMP[-1]]
    idx = [round(i * (len(EPOCH_RAMP) - 1) / (n - 1)) for i in range(n)]
    return [EPOCH_RAMP[i] for i in idx]


def apply_style():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": BASELINE,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "text.color": INK,
        "lines.linewidth": 2.0,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "font.family": "sans-serif",
    })


def direct_labels(ax, entries, dx=6, min_sep_px=11):
    """Label lines at their endpoints, nudging colliding labels apart.

    entries: list of (x, y, text, color). Call AFTER all plotting and axis
    scaling — collision resolution works in display pixels.
    """
    if not entries:
        return
    trans = ax.transData
    items = sorted(entries, key=lambda e: trans.transform((e[0], e[1]))[1])
    ypix = [trans.transform((x, y))[1] for x, y, _, _ in items]
    orig = list(ypix)
    for i in range(1, len(ypix)):
        if ypix[i] - ypix[i - 1] < min_sep_px:
            ypix[i] = ypix[i - 1] + min_sep_px
    for (x, y, text, color), yp, y0 in zip(items, ypix, orig):
        ax.annotate(text, (x, y), xytext=(dx, yp - y0),
                    textcoords="offset pixels", color=color, fontsize=8,
                    fontweight="bold", va="center", annotation_clip=False)
