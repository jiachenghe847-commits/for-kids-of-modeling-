import numpy as np
from .model import t_test, anova, chi_square, correlation, normality_test


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
