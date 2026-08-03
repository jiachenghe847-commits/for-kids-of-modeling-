"""由 artifacts/results.json 和附件原始数据生成论文用图。

这个脚本不做任何计算判断：所有参数都从 results.json 里取，只负责把已经算好的
东西画出来。改模型请改 compute.py，然后重跑本脚本。

在仓库根目录运行::

    .venv/bin/python drills/2025-B-sic-epilayer/src/make_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parent
REPO_ROOT = CASE_DIR.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT))

from compute import ATTACHMENTS, INPUT_DIR, model_reflectance, rebuild_permittivity  # noqa: E402
from inversion import _optical_path_spectrum  # noqa: E402
from optics import finesse_coefficient  # noqa: E402
from snippets.plotting.style import apply_cumcm_style  # noqa: E402
from spectra import band_mask, load_spectrum  # noqa: E402

FIG_DIR = CASE_DIR / "paper" / "figures"
LABEL = {"attachment_1": "附件 1（碳化硅，10°）", "attachment_2": "附件 2（碳化硅，15°）",
         "attachment_3": "附件 3（硅，10°）", "attachment_4": "附件 4（硅，15°）"}


def load_all():
    results = json.loads((CASE_DIR / "artifacts" / "results.json").read_text(encoding="utf-8"))
    spectra = {key: load_spectrum(INPUT_DIR / info["file"]) for key, info in ATTACHMENTS.items()}
    return results, spectra


def fig_overview(spectra):
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 6.0), sharex=True)
    for ax, key in zip(axes.ravel(), ATTACHMENTS):
        data = spectra[key]
        ax.plot(data["wavenumber_cm-1"], data["reflectance"] * 100, lw=0.6)
        ax.set_title(LABEL[key])
        ax.set_ylabel("反射率 / %")
    for ax in axes[1]:
        ax.set_xlabel("波数 $\\tilde\\nu$ / cm$^{-1}$")
    axes[0, 0].axvspan(797, 971, color="#A61B1B", alpha=0.12)
    axes[0, 1].axvspan(797, 971, color="#A61B1B", alpha=0.12)
    axes[0, 0].annotate("剩余射线带", xy=(884, 60), ha="center", fontsize=8.5, color="#A61B1B")
    fig.savefig(FIG_DIR / "fig_overview.png")
    plt.close(fig)


def fig_model_fit(results, spectra, key, name):
    """实测谱与两种模型的对比，下方是残差。多光束是否必要，看残差就够了。"""
    item = results["attachments"][key]
    data = spectra[key]
    v, r = data["wavenumber_cm-1"], data["reflectance"]
    theta, wafer = item["theta_deg"], item["wafer"]

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9.0, 5.6), sharex=True, height_ratios=[2.4, 1.0]
    )
    top.plot(v, r * 100, lw=0.7, color="#404040", label="实测")
    for kind, style, colour in (("two_beam", "--", "#C47F00"), ("airy", "-", "#A61B1B")):
        model = model_reflectance(wafer, kind, item[f"fit_{kind}"]["params"], v, theta)
        label = ("双光束模型（问题一）" if kind == "two_beam" else "多光束模型（问题三）")
        rms = item[f"fit_{kind}"]["rms_reflectance"] * 100
        top.plot(v, model * 100, style, lw=1.0, color=colour, label=f"{label}，RMS {rms:.3f}%")
        bottom.plot(v, (model - r) * 100, style, lw=0.7, color=colour)
    top.set_ylabel("反射率 / %")
    top.legend(loc="best")
    top.set_title(f"{name}：全谱拟合")
    bottom.axhline(0.0, color="#808080", lw=0.6)
    bottom.set_ylabel("残差 / %")
    bottom.set_xlabel("波数 $\\tilde\\nu$ / cm$^{-1}$")
    fig.savefig(FIG_DIR / f"fig_fit_{key}.png")
    plt.close(fig)


def fig_fourier(results, spectra):
    """低波数与高波数两段的光程谱，二次谐波的有无一眼可辨。"""
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 5.6))
    for row, key in enumerate(("attachment_1", "attachment_3")):
        data = spectra[key]
        v, r = data["wavenumber_cm-1"], data["reflectance"]
        for col, (lo, hi) in enumerate([(1000.0, 1800.0), (2600.0, 4000.0)]):
            ax = axes[row, col]
            path, amp, _ = _optical_path_spectrum(v, r, lo, hi, 3, 2**19)
            sel = (path > 5.0) & (path < 130.0)
            peak = path[sel][int(np.argmax(amp[sel]))]
            ax.plot(path[sel], amp[sel] / amp[sel].max(), lw=0.9)
            ax.axvline(peak, color="#2E7D32", lw=0.8, ls=":")
            ax.axvline(2 * peak, color="#A61B1B", lw=0.8, ls="--")
            ax.annotate("基频", xy=(peak, 1.02), ha="center", fontsize=8, color="#2E7D32")
            ax.annotate("2 倍频", xy=(2 * peak, 0.6), ha="center", fontsize=8, color="#A61B1B")
            ax.set_title(f"{LABEL[key]}  {lo:.0f}–{hi:.0f} cm$^{{-1}}$", fontsize=9.5)
            ax.set_xlabel("光程 $2nd\\cos\\theta_t$ / µm")
            ax.set_ylabel("归一化幅度")
            ax.set_ylim(0, 1.12)
    fig.savefig(FIG_DIR / "fig_fourier.png")
    plt.close(fig)


def fig_dispersion_and_finesse(results, spectra):
    """左：拟合出的外延层折射率色散；右：多光束判据 |r01·r12| 随波数的衰减。"""
    fig, (left, right) = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for key, colour in (("attachment_1", "#1F4E79"), ("attachment_3", "#A61B1B")):
        item = results["attachments"][key]
        data = spectra[key]
        v = data["wavenumber_cm-1"]
        mask = band_mask(v, 420.0, 4000.0)
        eps1, eps2 = rebuild_permittivity(item["wafer"], item["fit_airy"]["params"], v[mask])
        left.plot(v[mask], np.real(np.sqrt(eps1)), lw=1.1, color=colour, label=LABEL[key])
        right.semilogy(v[mask], finesse_coefficient(eps1, eps2, item["theta_deg"]),
                       lw=1.1, color=colour, label=LABEL[key])
    left.set_ylim(0, 8)
    left.set_xlabel("波数 $\\tilde\\nu$ / cm$^{-1}$")
    left.set_ylabel("外延层折射率 $n_1$")
    left.set_title("拟合得到的折射率色散")
    left.legend(fontsize=8)
    right.axhline(0.05, color="#808080", ls="--", lw=0.8)
    right.annotate("$|r_{01}r_{12}|=0.05$", xy=(2600, 0.056), fontsize=8, color="#606060")
    right.set_xlabel("波数 $\\tilde\\nu$ / cm$^{-1}$")
    right.set_ylabel("$|r_{01}r_{12}|$")
    right.set_title("多光束判据随波数的衰减")
    right.legend(fontsize=8)
    fig.savefig(FIG_DIR / "fig_dispersion.png")
    plt.close(fig)


def fig_convergence(results):
    """五个固定种子的收敛轨迹：报告的解不是某一个初值的产物。"""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4))
    for ax, key in zip(axes, ("attachment_1", "attachment_3")):
        for run in results["attachments"][key]["fit_airy"]["runs"]:
            trace = run["convergence_trace"]
            ax.semilogy(np.arange(1, len(trace) + 1), trace, lw=1.0, label=f"种子 {run['seed']}")
        ax.set_xlabel("目标函数求值次数")
        ax.set_ylabel("残差平方和 $\\frac{1}{2}\\|r\\|^2$")
        ax.set_title(f"{LABEL[key]}：多起点收敛")
        ax.legend(fontsize=8, ncol=2)
    fig.savefig(FIG_DIR / "fig_convergence.png")
    plt.close(fig)


def main() -> None:
    apply_cumcm_style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    results, spectra = load_all()
    fig_overview(spectra)
    fig_model_fit(results, spectra, "attachment_1", LABEL["attachment_1"])
    fig_model_fit(results, spectra, "attachment_3", LABEL["attachment_3"])
    fig_fourier(results, spectra)
    fig_dispersion_and_finesse(results, spectra)
    fig_convergence(results)
    for path in sorted(FIG_DIR.glob("*.png")):
        print(f"  {path.relative_to(CASE_DIR)}  {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
