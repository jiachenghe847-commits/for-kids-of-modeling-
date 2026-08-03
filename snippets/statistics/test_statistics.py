import numpy as np
import pytest

from .model import (
    anova,
    bootstrap_ci,
    chi_square,
    coefficient_of_variation,
    confidence_interval,
    correlation,
    normality_test,
    t_test,
)


def test_two_sample_t_detects_difference():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 100)
    b = rng.normal(2, 1, 100)   # 均值差 2，应显著
    result = t_test(a, b)
    assert result["significant"] is True
    assert result["kind"] == "two-sample"


def test_one_sample_t_no_difference():
    rng = np.random.default_rng(1)
    a = rng.normal(5, 1, 200)
    result = t_test(a, popmean=5)   # 真均值就是 5，不应显著
    assert result["significant"] is False


def test_anova_detects_group_difference():
    rng = np.random.default_rng(2)
    g1 = rng.normal(0, 1, 50)
    g2 = rng.normal(0, 1, 50)
    g3 = rng.normal(3, 1, 50)   # 第三组明显不同
    result = anova(g1, g2, g3)
    assert result["significant"] is True


def test_chi_square_independence():
    # 强关联的列联表 -> 显著
    table = [[40, 10], [10, 40]]
    result = chi_square(table)
    assert result["significant"] is True
    assert result["dof"] == 1


def test_correlation_strong_positive():
    x = np.arange(50, dtype=float)
    y = 2 * x + 1
    result = correlation(x, y, method="pearson")
    assert result["r"] > 0.99
    assert result["significant"] is True


def test_normality_on_normal_data():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 1, 300)
    assert normality_test(x)["normal"] is True


def test_confidence_interval_brackets_the_true_mean():
    rng = np.random.default_rng(4)
    x = rng.normal(10.0, 2.0, 200)
    result = confidence_interval(x)
    assert result["ci_low"] < 10.0 < result["ci_high"]
    assert result["ci_low"] < result["mean"] < result["ci_high"]
    assert result["df"] == 199


def test_confidence_interval_narrows_as_the_sample_grows():
    rng = np.random.default_rng(5)
    small = confidence_interval(rng.normal(0, 1, 20))["half_width"]
    large = confidence_interval(rng.normal(0, 1, 2000))["half_width"]
    assert large < small / 5


def test_coefficient_of_variation_is_scale_free():
    """CV 的意义就在于跨量纲可比：同一组数据换单位，CV 不变。"""
    x = np.array([10.0, 11.0, 12.0, 13.0])
    assert coefficient_of_variation(x)["cv_percent"] == pytest.approx(
        coefficient_of_variation(x * 1000)["cv_percent"]
    )


def test_coefficient_of_variation_refuses_to_report_near_zero_mean():
    """均值趋零时 CV 会被分母放大成任意值，必须标成不可用而不是照报。"""
    result = coefficient_of_variation([-1.0, 1.0, -1.0, 1.0])
    assert result["meaningful"] is False
    assert np.isnan(result["cv_percent"])


def test_bootstrap_ci_agrees_with_the_t_interval_on_normal_data():
    """正态数据上两种区间应当接近——不接近说明其中一个实现错了。"""
    rng = np.random.default_rng(6)
    x = rng.normal(5.0, 1.0, 300)
    t_ci = confidence_interval(x)
    bs = bootstrap_ci(x, n_resamples=2000, seed=7)
    assert bs["ci_low"] == pytest.approx(t_ci["ci_low"], abs=0.05)
    assert bs["ci_high"] == pytest.approx(t_ci["ci_high"], abs=0.05)


def test_bootstrap_ci_works_for_the_median_where_t_interval_does_not_apply():
    rng = np.random.default_rng(8)
    x = rng.lognormal(0.0, 1.0, 400)
    result = bootstrap_ci(x, statistic=np.median, n_resamples=2000, seed=9)
    assert result["ci_low"] < np.median(x) < result["ci_high"]


def test_bootstrap_ci_is_reproducible_given_a_seed():
    """同种子必须给同结果，否则论文里的区间是不可复现的。"""
    rng = np.random.default_rng(10)
    x = rng.normal(0, 1, 100)
    first = bootstrap_ci(x, n_resamples=1000, seed=11)
    second = bootstrap_ci(x, n_resamples=1000, seed=11)
    assert first["ci_low"] == second["ci_low"]
    assert first["ci_high"] == second["ci_high"]
