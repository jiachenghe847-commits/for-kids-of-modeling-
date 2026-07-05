import numpy as np
from .model import entropy_weights, topsis_score


def test_entropy_weights_sum_to_one():
    matrix = np.array([[1, 10], [2, 8], [3, 6], [4, 4]], dtype=float)
    weights = entropy_weights(matrix)
    assert abs(weights.sum() - 1.0) < 1e-9


def test_topsis_score_ranks_best_alternative_highest():
    # 两个指标都是越大越好，第 4 行 (4,4) 综合应不弱于第 1 行 (1,10) 之外的中间行
    matrix = np.array([[1, 10], [2, 8], [3, 6], [10, 10]], dtype=float)
    weights = np.array([0.5, 0.5])
    scores = topsis_score(matrix, weights)
    assert scores.argmax() == 3  # 第 4 行两个指标都最大，应该排第一
