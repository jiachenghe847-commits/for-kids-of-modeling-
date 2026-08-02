import matplotlib.pyplot as plt

_CHINESE_FONTS = [
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
    "DejaVu Sans",
]

_PALETTE = ["#1F4E79", "#A61B1B", "#2E7D32", "#C47F00", "#6A4C93", "#4F6D7A"]


def apply_cumcm_style() -> None:
    """Apply the shared B226-style competition plotting defaults."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": _CHINESE_FONTS,
            "mathtext.fontset": "stix",
            "axes.unicode_minus": False,
            "figure.dpi": 110,
            "figure.figsize": (7.2, 4.5),
            "figure.constrained_layout.use": True,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.06,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 10.5,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#D9D9D9",
            "grid.linewidth": 0.55,
            "grid.alpha": 0.75,
            "lines.linewidth": 1.8,
            "lines.markersize": 4.5,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "legend.frameon": False,
            "axes.prop_cycle": plt.cycler(color=_PALETTE),
        }
    )
