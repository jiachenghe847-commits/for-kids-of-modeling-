import numpy as np
import pytest
from sklearn.linear_model import LinearRegression
from .model import (
    compare_objectives,
    compare_tabular_records,
    constraint_residual_report,
    cross_validate_score,
    joint_fit,
    multi_seed_summary,
    parse_number,
    residual_stats,
    sensitivity_analysis,
    subrange_drift_scan,
)


def _two_condition_datasets(noise=0.3, seed=0, slope=2.5, intercepts=(1.0, -0.5)):
    """两组数据共享斜率、各有截距——2025-B 双角共享厚度的最小复现。"""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 10, 60)
    return [{"x": x, "y": slope * x + b + rng.normal(0, noise, x.size)} for b in intercepts]


def _linear(shared, local, data):
    return shared["a"] * data["x"] + local["b"]


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


def test_joint_fit_recovers_the_shared_parameter():
    result = joint_fit(_two_condition_datasets(), _linear, ["a"], ["b"], [1.0], [[0.0], [0.0]])
    assert result["success"]
    assert result["shared"]["a"] == pytest.approx(2.5, abs=0.03)
    assert result["local"][0]["b"] == pytest.approx(1.0, abs=0.15)
    assert result["local"][1]["b"] == pytest.approx(-0.5, abs=0.15)


def test_joint_fit_reports_the_spread_that_separate_fits_would_have_produced():
    """报告里要写的是这一项：不联合的话，本该相同的参数会散布多少。"""
    result = joint_fit(_two_condition_datasets(), _linear, ["a"], ["b"], [1.0], [[0.0], [0.0]])
    comparison = result["comparison"]["a"]
    assert len(comparison["separate"]) == 2
    assert comparison["separate_half_spread"] > 0
    # 联合解不该跑到两个单独解的区间之外
    assert min(comparison["separate"]) <= comparison["joint"] <= max(comparison["separate"])
    assert comparison["separate_relative_spread"] == pytest.approx(
        comparison["separate_half_spread"] / abs(comparison["separate_mean"])
    )


def test_joint_fit_beats_averaging_separate_fits_on_noisy_data():
    """联合拟合的意义在于精度，不只是形式好看——噪声大时优势才看得出来。

    各组单独拟合再平均，等于扔掉了「斜率必须相同」这条硬约束。
    """
    joint_errors, mean_errors = [], []
    for seed in range(12):
        result = joint_fit(_two_condition_datasets(noise=1.5, seed=seed), _linear,
                           ["a"], ["b"], [1.0], [[0.0], [0.0]])
        comparison = result["comparison"]["a"]
        joint_errors.append(abs(comparison["joint"] - 2.5))
        mean_errors.append(abs(comparison["separate_mean"] - 2.5))
    assert np.mean(joint_errors) <= np.mean(mean_errors) * 1.05


def test_joint_fit_rejects_mismatched_initial_guess_shape():
    with pytest.raises(ValueError):
        joint_fit(_two_condition_datasets(), _linear, ["a"], ["b"], [1.0], [[0.0]])


def test_subrange_drift_scan_detects_a_monotone_drift():
    x = np.linspace(1.0, 10.0, 400)
    # 估计量随所用区间线性平移——典型的「模型里少建了一项」的表现
    result = subrange_drift_scan(x, np.zeros_like(x),
                                 lambda xs, ys: float(xs.mean() * 0.1 + 1.0),
                                 [(1, 4), (4, 7), (7, 10)])
    assert result["monotonic"] is True
    assert result["drift_relative"] > 0.3
    assert result["values"][0] < result["values"][-1]


def test_subrange_drift_scan_stays_flat_when_there_is_no_systematic_effect():
    rng = np.random.default_rng(3)
    x = np.linspace(0.0, 10.0, 600)
    y = 4.0 + rng.normal(0, 0.01, x.size)
    result = subrange_drift_scan(x, y, lambda xs, ys: float(ys.mean()),
                                 [(0, 3), (3, 6), (6, 10)])
    assert result["drift_relative"] < 0.01
    assert result["full_range_value"] == pytest.approx(4.0, abs=0.01)


def test_subrange_drift_scan_refuses_an_empty_window():
    x = np.linspace(0.0, 10.0, 50)
    with pytest.raises(ValueError):
        subrange_drift_scan(x, x, lambda xs, ys: float(ys.mean()), [(100, 200)])


def test_parse_number_preserves_negative_sign_and_decimal():
    assert parse_number(" -12.50 ") == pytest.approx(-12.5)
    assert parse_number("1,234.5") == pytest.approx(1234.5)
    with pytest.raises(ValueError):
        parse_number("12 units")
    with pytest.raises(ValueError):
        parse_number("nan")


def test_compare_tabular_records_catches_roundtrip_value_changes():
    expected = [{"id": "A", "shift": -1.25}, {"id": "B", "shift": 2.0}]
    observed = [{"id": "B", "shift": "2.000"}, {"id": "A", "shift": "-1.20"}]
    report = compare_tabular_records(expected, observed, ["shift"], key_field="id", tolerances=0.01)
    assert report["matched"] is False
    assert report["mismatches"][0]["key"] == "A"


def test_compare_tabular_records_rejects_duplicate_keys():
    with pytest.raises(ValueError):
        compare_tabular_records([{"id": "A", "x": 1}],
                                [{"id": "A", "x": 1}, {"id": "A", "x": 1}],
                                ["x"], key_field="id")
