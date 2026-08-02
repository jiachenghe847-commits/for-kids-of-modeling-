import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle
from matplotlib.figure import Figure
from pathlib import Path
import textwrap


def sensitivity_curve(
    x: np.ndarray,
    series: dict,
    xlabel: str,
    ylabel: str,
    baseline: float | None = None,
) -> Figure:
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    for label, y in series.items():
        ax.plot(x, y, marker="o", label=label)
    if baseline is not None:
        ax.axhline(baseline, color="gray", linestyle="--", linewidth=1, label="基准值")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    return fig


def heatmap(
    matrix: np.ndarray,
    row_labels: list,
    col_labels: list,
    cbar_label: str,
    annotate: bool = True,
) -> Figure:
    fig, ax = plt.subplots(figsize=(max(6.4, len(col_labels) * 0.72), max(4.2, len(row_labels) * 0.52)))
    im = ax.imshow(matrix, cmap="coolwarm", aspect="auto")
    ax.set_xticks(range(len(col_labels)), labels=col_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)), labels=row_labels)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)
    ax.grid(False)
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
        2, 1, figsize=(7.2, 5.8), sharex=True, height_ratios=[3, 1]
    )
    ax_fit.scatter(x, y_true, s=20, label="原始数据", zorder=3)
    order = np.argsort(x)
    ax_fit.plot(x[order], y_fit[order], color="#C82423", label="拟合曲线", zorder=2)
    ax_fit.set_ylabel(ylabel)
    ax_fit.legend()

    residual = y_true - y_fit
    ax_resid.scatter(x, residual, s=15, color="#54B345")
    ax_resid.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax_resid.set_xlabel(xlabel)
    ax_resid.set_ylabel("残差")
    return fig


def convergence_curve(
    iterations: np.ndarray,
    values: np.ndarray,
    ylabel: str = "损失",
    log_scale: bool = True,
) -> Figure:
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.plot(iterations, values, color="#2878B5")
    if log_scale:
        ax.set_yscale("log")
    ax.set_xlabel("迭代次数")
    ax.set_ylabel(ylabel)
    return fig


def multi_panel(
    panels: list,
    nrows: int,
    ncols: int,
    titles: list,
) -> Figure:
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.5 * ncols, 3.0 * nrows))
    axes_flat = np.atleast_1d(axes).flatten()
    for ax, (x, y), title in zip(axes_flat, panels, titles):
        ax.plot(x, y, marker="o", markersize=3)
        ax.set_title(title)
    for ax in axes_flat[len(panels):]:
        ax.axis("off")
    return fig


def workflow_diagram(
    nodes: list[str],
    edges: list[tuple[str, str]],
    groups: dict[str, list[str]] | None = None,
    title: str | None = None,
    output_path: str | Path | None = None,
) -> Figure:
    """Draw a compact, deterministic workflow diagram for a paper.

    Nodes are placed in a three-column serpentine grid. ``groups`` maps a
    legend label to its node labels and only controls fill color.
    """
    if not nodes:
        raise ValueError("nodes must not be empty")
    if len(set(nodes)) != len(nodes):
        raise ValueError("node labels must be unique")

    known = set(nodes)
    unknown = {name for edge in edges for name in edge if name not in known}
    if unknown:
        raise ValueError(f"edges reference unknown nodes: {sorted(unknown)}")

    palette = ["#DCE8F2", "#F2DEDE", "#E0EBDD", "#F4E8CF", "#E8E0F0", "#DEE8EA"]
    node_colors = {node: palette[0] for node in nodes}
    group_handles = []
    if groups:
        for index, (label, members) in enumerate(groups.items()):
            color = palette[index % len(palette)]
            for member in members:
                if member not in known:
                    raise ValueError(f"group references unknown node: {member}")
                node_colors[member] = color
            group_handles.append(Patch(facecolor=color, edgecolor="#5B6573", label=label))

    ncols = min(3, len(nodes))
    nrows = int(np.ceil(len(nodes) / ncols))
    fig_height = max(2.6, 1.65 * nrows + (0.45 if title else 0))
    fig, ax = plt.subplots(figsize=(7.2, fig_height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    xs = np.linspace(0.16, 0.84, ncols)
    ys = np.linspace(0.78, 0.22, nrows) if nrows > 1 else np.array([0.5])
    positions = {}
    for index, node in enumerate(nodes):
        row, col = divmod(index, ncols)
        visual_col = col if row % 2 == 0 else ncols - 1 - col
        positions[node] = (float(xs[visual_col]), float(ys[row]))

    box_width = min(0.25, 0.72 / ncols)
    box_height = min(0.18, 0.50 / nrows)
    for source, target in edges:
        arrow = FancyArrowPatch(
            positions[source],
            positions[target],
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color="#5B6573",
            shrinkA=31,
            shrinkB=31,
            connectionstyle="arc3,rad=0",
            zorder=1,
        )
        ax.add_patch(arrow)

    for node in nodes:
        x, y = positions[node]
        rect = Rectangle(
            (x - box_width / 2, y - box_height / 2),
            box_width,
            box_height,
            facecolor=node_colors[node],
            edgecolor="#3F4B59",
            linewidth=1.0,
            zorder=2,
        )
        ax.add_patch(rect)
        wrapped = "\n".join(textwrap.wrap(node, width=10, break_long_words=True))
        ax.text(x, y, wrapped, ha="center", va="center", fontsize=9.5, zorder=3)

    if title:
        ax.set_title(title, pad=8)
    if group_handles:
        ax.legend(handles=group_handles, loc="lower center", ncol=min(3, len(group_handles)),
                  bbox_to_anchor=(0.5, -0.04))
    if output_path is not None:
        fig.savefig(Path(output_path))
    return fig
