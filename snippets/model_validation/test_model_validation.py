import numpy as np
from sklearn.linear_model import LinearRegression
from .model import residual_stats, cross_validate_score, sensitivity_analysis


def test_residual_stats_perfect_fit():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    result = residual_stats(y, y)
    assert abs(result["r2"] - 1.0) < 1e-12
    assert result["rmse"] < 1e-12
    assert result["mae"] < 1e-12


def test_residual_stats_known_error():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([11.0, 19.0, 30.0])  # 误差 1, -1, 0
    result = residual_stats(y_true, y_pred)
    assert abs(result["mae"] - (2 / 3)) < 1e-9


def test_cross_validate_linear():
    rng = np.random.default_rng(0)
    X = rng.normal(0, 1, (60, 3))
    y = X @ np.array([1.0, -2.0, 0.5]) + 0.01 * rng.normal(0, 1, 60)
    result = cross_validate_score(LinearRegression(), X, y, k=5, scoring="r2")
    assert result["mean"] > 0.99


def test_sensitivity_detects_dominant_param():
    # f = 10*a + 1*b ，对 a 更敏感
    result = sensitivity_analysis(lambda p: 10 * p["a"] + p["b"], {"a": 1.0, "b": 1.0})
    assert result["per_param"]["a"]["elasticity"] > result["per_param"]["b"]["elasticity"]
