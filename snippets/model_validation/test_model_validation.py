import numpy as np
import pytest
from sklearn.linear_model import LinearRegression
from .model import (
    compare_objectives,
    constraint_residual_report,
    cross_validate_score,
    multi_seed_summary,
    residual_stats,
    sensitivity_analysis,
)


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


def test_multi_seed_summary_preserves_runs_and_direction():
    summary = multi_seed_summary(
        lambda seed: {
            "objective": np.float64((seed - 2) ** 2),
            "x": np.array([seed, seed + 1]),
            "seed": 999,
        },
        seeds=[1, 2, 3],
        sense="min",
    )
    assert summary["best_seed"] == 2
    assert summary["best_objective"] == 0.0
    assert summary["worst_objective"] == 1.0
    assert len(summary["runs"]) == 3
    assert summary["runs"][0]["seed"] == 1
    assert summary["runs"][0]["x"] == [1, 2]


def test_compare_objectives_uses_consistent_degradation_sign():
    assert compare_objectives(11, 10, sense="min")["degradation"] == 1
    assert compare_objectives(9, 10, sense="max")["degradation"] == 1
    assert compare_objectives(11, 10, sense="max")["candidate_is_better"]
    with pytest.raises(ValueError):
        compare_objectives(1, 1, sense="unknown")


def test_constraint_residual_report_handles_all_relations():
    report = constraint_residual_report(
        [
            {"name": "capacity", "lhs": 9.0, "relation": "<=", "rhs": 10.0},
            {"name": "demand", "lhs": 5.0, "relation": ">=", "rhs": 5.0},
            {"name": "balance", "lhs": 3.01, "relation": "==", "rhs": 3.0, "tolerance": 0.001},
        ]
    )
    assert not report["feasible"]
    assert report["violated"] == ["balance"]
    assert report["max_violation"] == pytest.approx(0.009)
