import numpy as np
from .model import ahp_weights


def test_ahp_weights_on_consistent_matrix():
    # 3 个方案，两两比较矩阵完全一致（A 比 B 重 2 倍，B 比 C 重 2 倍，A 比 C 重 4 倍）
    matrix = np.array([
        [1, 2, 4],
        [1 / 2, 1, 2],
        [1 / 4, 1 / 2, 1],
    ])
    result = ahp_weights(matrix)
    assert result["consistent"] is True
    assert abs(sum(result["weights"]) - 1.0) < 1e-9
    assert result["weights"][0] > result["weights"][1] > result["weights"][2]
