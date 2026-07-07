import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def sensitivity_curve(
    x: np.ndarray,
    series: dict,
    xlabel: str,
    ylabel: str,
    baseline: float | None = None,
) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    for label, y in series.items():
        ax.plot(x, y, marker="o", markersize=4, label=label)
    if baseline is not None:
        ax.axhline(baseline, color="gray", linestyle="--", linewidth=1, label="基准值")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(alpha=0.3)
    return fig


def heatmap(
    matrix: np.ndarray,
    row_labels: list,
    col_labels: list,
    cbar_label: str,
    annotate: bool = True,
) -> Figure:
    fig, ax = plt.subplots(figsize=(max(6, len(col_labels) * 0.8), max(5, len(row_labels) * 0.6)))
    im = ax.imshow(matrix, cmap="coolwarm", aspect="auto")
    ax.set_xticks(range(len(col_labels)), labels=col_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)), labels=row_labels)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    if annotate:
        vmax = np.nanmax(np.abs(matrix)) if matrix.size else 1.0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                val = matrix[i, j]
                color = "white" if abs(val) > vmax * 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=8)
    return fig


def fit_comparison(
    x: np.ndarray,
    y_true: np.ndarray,
    y_fit: np.ndarray,
    xlabel: str,
    ylabel: str,
) -> Figure:
    fig, (ax_fit, ax_resid) = plt.subplots(
        2, 1, figsize=(8, 7), sharex=True, height_ratios=[3, 1]
    )
    ax_fit.scatter(x, y_true, s=20, label="原始数据", zorder=3)
    order = np.argsort(x)
    ax_fit.plot(x[order], y_fit[order], color="#C82423", label="拟合曲线", zorder=2)
    ax_fit.set_ylabel(ylabel)
    ax_fit.legend()
    ax_fit.grid(alpha=0.3)

    residual = y_true - y_fit
    ax_resid.scatter(x, residual, s=15, color="#54B345")
    ax_resid.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax_resid.set_xlabel(xlabel)
    ax_resid.set_ylabel("残差")
    ax_resid.grid(alpha=0.3)
    return fig


def convergence_curve(
    iterations: np.ndarray,
    values: np.ndarray,
    ylabel: str = "损失",
    log_scale: bool = True,
) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(iterations, values, color="#2878B5")
    if log_scale:
        ax.set_yscale("log")
    ax.set_xlabel("迭代次数")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    return fig


def multi_panel(
    panels: list,
    nrows: int,
    ncols: int,
    titles: list,
) -> Figure:
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3.5 * nrows))
    axes_flat = np.atleast_1d(axes).flatten()
    for ax, (x, y), title in zip(axes_flat, panels, titles):
        ax.plot(x, y, marker="o", markersize=3)
        ax.set_title(title)
        ax.grid(alpha=0.3)
    for ax in axes_flat[len(panels):]:
        ax.axis("off")
    fig.tight_layout()
    return fig
