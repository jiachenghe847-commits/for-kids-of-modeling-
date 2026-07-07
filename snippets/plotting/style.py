import matplotlib.pyplot as plt

_CHINESE_FONTS = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Zen Hei"]

_PALETTE = ["#2878B5", "#C82423", "#9AC9DB", "#F8AC8C", "#54B345", "#32B897"]


def apply_cumcm_style() -> None:
    plt.rcParams["font.sans-serif"] = _CHINESE_FONTS
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=_PALETTE)
