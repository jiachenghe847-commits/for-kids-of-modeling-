import numpy as np
from .model import transition_matrix, stationary_distribution, n_step_distribution, predict_next


def test_transition_matrix_rows_sum_to_one():
    seq = [0, 1, 0, 1, 0, 1, 2, 0]
    result = transition_matrix(seq, n_states=3)
    P = result["P"]
    # 出现过的状态行应和为 1
    assert abs(P[0].sum() - 1.0) < 1e-9
    assert abs(P[1].sum() - 1.0) < 1e-9


def test_stationary_distribution_known_chain():
    # 已知 2 状态链，平稳分布可解析求：pi ∝ [b, a]，此处 P=[[0.9,0.1],[0.5,0.5]]
    P = np.array([[0.9, 0.1], [0.5, 0.5]])
    result = stationary_distribution(P)
    pi = result["pi"]
    assert abs(pi.sum() - 1.0) < 1e-9
    # 解析解 pi = [5/6, 1/6]
    assert np.allclose(pi, [5 / 6, 1 / 6], atol=1e-6)
    # 平稳分布应满足 pi = pi P
    assert np.allclose(pi @ P, pi, atol=1e-9)


def test_n_step_converges_to_stationary():
    P = np.array([[0.9, 0.1], [0.5, 0.5]])
    result = n_step_distribution(P, initial=[1.0, 0.0], n=100)
    assert np.allclose(result["distribution"], [5 / 6, 1 / 6], atol=1e-4)


def test_predict_next_picks_max():
    P = np.array([[0.2, 0.8], [0.6, 0.4]])
    result = predict_next(P, current_state=0)
    assert result["most_likely"] == 1
