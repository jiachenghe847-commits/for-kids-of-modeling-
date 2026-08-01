import numpy as np
from .model import pca_reduce, pca_composite_score, factor_analysis, canonical_correlation


def test_pca_captures_dominant_direction():
    # 一条主要沿 (1,1) 方向的数据，第一主成分应吃掉绝大部分方差
    rng = np.random.default_rng(0)
    t = rng.normal(0, 5, 100)
    X = np.column_stack([t + rng.normal(0, 0.1, 100), t + rng.normal(0, 0.1, 100)])
    result = pca_reduce(X, n_components=2)
    assert result["explained_ratio"][0] > 0.95
    assert abs(result["cumulative_ratio"][-1] - 1.0) < 1e-6


def test_pca_fraction_keeps_enough_components():
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, (50, 5))
    result = pca_reduce(X, n_components=0.9)
    assert result["cumulative_ratio"][-1] >= 0.9


def test_composite_score_ranks_samples():
    # 三行，逐行整体更大，标准化后综合得分应单调
    X = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    result = pca_composite_score(X)
    assert set(result["rank"].tolist()) == {1, 2, 3}


def test_factor_analysis_recovers_two_factors():
    # 构造 2 个潜在因子驱动 6 个指标
    rng = np.random.default_rng(0)
    f1 = rng.normal(0, 1, 200)
    f2 = rng.normal(0, 1, 200)
    X = np.column_stack([
        f1 + 0.1 * rng.normal(0, 1, 200), f1 + 0.1 * rng.normal(0, 1, 200),
        f1 + 0.1 * rng.normal(0, 1, 200), f2 + 0.1 * rng.normal(0, 1, 200),
        f2 + 0.1 * rng.normal(0, 1, 200), f2 + 0.1 * rng.normal(0, 1, 200),
    ])
    result = factor_analysis(X, n_factors=2)
    assert result["loadings"].shape == (2, 6)
    assert result["scores"].shape == (200, 2)
    # 每个指标都应被公共因子较好解释
    assert (result["communality"] > 0.5).all()


def test_canonical_correlation_finds_strong_link():
    rng = np.random.default_rng(1)
    latent = rng.normal(0, 1, 200)
    X = np.column_stack([latent + 0.1 * rng.normal(0, 1, 200), rng.normal(0, 1, 200)])
    Y = np.column_stack([latent + 0.1 * rng.normal(0, 1, 200), rng.normal(0, 1, 200)])
    result = canonical_correlation(X, Y, n_components=1)
    assert abs(result["correlations"][0]) > 0.9   # 共享潜变量 -> 强典型相关
