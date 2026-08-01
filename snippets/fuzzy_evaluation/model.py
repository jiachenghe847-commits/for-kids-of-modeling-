import numpy as np


def fuzzy_comprehensive(R: np.ndarray, weights: np.ndarray, level_scores=None) -> dict:
    """模糊综合评价（加权平均型 M(·,+) 算子）。

    R: 隶属度矩阵，形状 (指标数 m, 评语等级数 n)，R[i, j] = 第 i 个指标对第 j 级评语的隶属度。
    weights: 各指标权重 (m,)，和应为 1（可来自 AHP / 熵权法）。
    level_scores: 各评语等级的分值 (n,)，如 [95, 85, 75, 60]；给了就额外算综合得分。
    """
    R = np.asarray(R, dtype=float)
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()

    b = w @ R                     # 综合隶属度向量 (n,)
    b = b / b.sum() if b.sum() > 0 else b
    level = int(np.argmax(b))     # 最大隶属度原则确定等级

    out = {"membership": b, "level_index": level}
    if level_scores is not None:
        s = np.asarray(level_scores, dtype=float)
        out["score"] = float(b @ s)
    return out


def fuzzy_evaluate_multi(R_list, weights, sub_weights, level_scores=None) -> dict:
    """两级模糊综合评价：先对每个准则层内部评价，再对准则层之间汇总。

    R_list: 长度为 K 的列表，每个是某准则下若干指标的隶属度矩阵 (m_k, n)。
    weights: 各准则内部指标权重列表，长度 K，第 k 个形状 (m_k,)。
    sub_weights: 准则层之间的权重 (K,)。
    """
    first_level = np.array(
        [fuzzy_comprehensive(R_list[k], weights[k])["membership"] for k in range(len(R_list))]
    )
    return fuzzy_comprehensive(first_level, sub_weights, level_scores)
