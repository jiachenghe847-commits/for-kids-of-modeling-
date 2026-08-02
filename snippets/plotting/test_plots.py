import matplotlib

matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt

from .style import apply_cumcm_style
from .plots import (
    convergence_curve,
    fit_comparison,
    heatmap,
    multi_panel,
    sensitivity_curve,
    workflow_diagram,
)

apply_cumcm_style()


def test_sensitivity_curve_runs():
    x = np.linspace(-800, 800, 20)
    series = {"开角100°": x * 0.2 + 200, "开角120°": x * 0.3 + 250}
    fig = sensitivity_curve(x, series, "距离/m", "覆盖宽度/m", baseline=300)
    assert fig is not None


def test_heatmap_runs():
    matrix = np.random.rand(4, 5)
    fig = heatmap(matrix, ["A", "B", "C", "D"], ["1", "2", "3", "4", "5"], "相关系数")
    assert fig is not None


def test_fit_comparison_runs():
    x = np.linspace(0, 10, 30)
    y_true = 2 * x + 1 + np.random.normal(0, 0.5, size=x.shape)
    y_fit = 2 * x + 1
    fig = fit_comparison(x, y_true, y_fit, "x", "y")
    assert fig is not None


def test_convergence_curve_runs():
    iterations = np.arange(1, 100)
    values = 1.0 / iterations
    fig = convergence_curve(iterations, values, ylabel="损失（残差平方和）")
    assert fig is not None


def test_multi_panel_runs():
    x = np.linspace(0, 1, 10)
    panels = [(x, x), (x, x**2), (x, x**3)]
    fig = multi_panel(panels, nrows=1, ncols=3, titles=["下肢角度", "躯干倾斜角度", "腿与地面夹角"])
    assert fig is not None


def test_competition_style_defaults():
    apply_cumcm_style()
    assert plt.rcParams["savefig.dpi"] == 300
    assert plt.rcParams["axes.spines.top"] is False
    assert plt.rcParams["axes.spines.right"] is False
    assert plt.rcParams["lines.linewidth"] == 1.8
    assert plt.rcParams["figure.figsize"] == [7.2, 4.5]


def test_workflow_diagram_saves_file(tmp_path):
    out = tmp_path / "workflow.png"
    nodes = ["数据预处理", "灰色预测", "综合评价", "网络优化", "结果检验"]
    edges = list(zip(nodes, nodes[1:]))
    fig = workflow_diagram(
        nodes,
        edges,
        groups={"数据层": nodes[:1], "模型层": nodes[1:4], "检验层": nodes[4:]},
        title="研究流程",
        output_path=out,
    )
    assert fig is not None
    assert out.is_file()
    assert out.stat().st_size > 0


def test_workflow_diagram_rejects_unknown_nodes():
    try:
        workflow_diagram(["数据"], [("数据", "结果")])
    except ValueError as exc:
        assert "unknown nodes" in str(exc)
    else:
        raise AssertionError("expected ValueError")
