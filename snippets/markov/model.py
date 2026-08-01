import numpy as np


def transition_matrix(sequence, n_states: int = None) -> dict:
    """从观测到的状态序列估计一步转移概率矩阵 P（按频率）。

    sequence: 整数状态序列，如 [0,1,1,2,0,...]。
    n_states: 状态总数；None 则取序列里出现的最大状态 +1。
    返回行随机矩阵 P，P[i, j] = 从状态 i 转移到 j 的概率。
    """
    seq = np.asarray(sequence, dtype=int)
    n = n_states if n_states is not None else int(seq.max()) + 1
    counts = np.zeros((n, n))
    for i, j in zip(seq[:-1], seq[1:]):
        counts[i, j] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0   # 从未出现的状态：留作零行避免除零
    P = counts / row_sums
    return {"P": P, "counts": counts, "n_states": n}


def stationary_distribution(P) -> dict:
    """求平稳分布 π（满足 π = πP）：P 转置的特征值 1 对应的左特征向量，归一化。"""
    P = np.asarray(P, dtype=float)
    eigvals, eigvecs = np.linalg.eig(P.T)
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    pi = np.real(eigvecs[:, idx])
    pi = pi / pi.sum()
    return {"pi": pi, "eigenvalue": float(np.real(eigvals[idx]))}


def n_step_distribution(P, initial, n: int) -> dict:
    """已知初始分布 initial（或初始状态的 one-hot），求 n 步后的状态分布 = initial @ P^n。"""
    P = np.asarray(P, dtype=float)
    initial = np.asarray(initial, dtype=float)
    Pn = np.linalg.matrix_power(P, n)
    dist = initial @ Pn
    return {"distribution": dist, "P_n": Pn}


def predict_next(P, current_state: int) -> dict:
    """给定当前状态，返回下一步各状态概率与最可能的状态。"""
    P = np.asarray(P, dtype=float)
    probs = P[current_state]
    return {"probs": probs, "most_likely": int(np.argmax(probs))}
