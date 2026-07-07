import matplotlib

matplotlib.use("Agg")

import numpy as np

from .style import apply_cumcm_style
from .plots import sensitivity_curve, heatmap, fit_comparison, convergence_curve, multi_panel

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
