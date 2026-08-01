import numpy as np
from .model import fuzzy_comprehensive, fuzzy_evaluate_multi


def test_fuzzy_picks_dominant_level():
    # 两个指标都强烈隶属于第 0 级（优），权重相等 -> 最终应判为第 0 级
    R = np.array([
        [0.7, 0.2, 0.1],
        [0.6, 0.3, 0.1],
    ])
    result = fuzzy_comprehensive(R, weights=[0.5, 0.5])
    assert result["level_index"] == 0
    assert abs(result["membership"].sum() - 1.0) < 1e-9


def test_fuzzy_score_with_level_scores():
    R = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    result = fuzzy_comprehensive(R, weights=[0.5, 0.5], level_scores=[100, 80, 60])
    # 隶属度 [0.5,0,0.5] -> 得分 0.5*100 + 0.5*60 = 80
    assert abs(result["score"] - 80.0) < 1e-9


def test_two_level_evaluation_runs():
    R1 = np.array([[0.8, 0.2], [0.6, 0.4]])
    R2 = np.array([[0.3, 0.7]])
    result = fuzzy_evaluate_multi(
        [R1, R2], weights=[[0.5, 0.5], [1.0]], sub_weights=[0.6, 0.4]
    )
    assert abs(result["membership"].sum() - 1.0) < 1e-9
