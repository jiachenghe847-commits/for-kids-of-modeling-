import numpy as np
from scipy import stats


def t_test(a, b=None, popmean=None, alpha: float = 0.05) -> dict:
    """t 检验。

    单样本：给 a 和 popmean，检验 a 的均值是否等于 popmean。
    双样本：给 a 和 b，检验两组均值是否有显著差异（独立样本，默认不假设等方差 Welch）。
    """
    a = np.asarray(a, dtype=float)
    if b is not None:
        b = np.asarray(b, dtype=float)
        stat, p = stats.ttest_ind(a, b, equal_var=False)
        kind = "two-sample"
    elif popmean is not None:
        stat, p = stats.ttest_1samp(a, popmean)
        kind = "one-sample"
    else:
        raise ValueError("双样本给 b，单样本给 popmean")
    return {"statistic": float(stat), "p_value": float(p),
            "significant": bool(p < alpha), "kind": kind}


def anova(*groups, alpha: float = 0.05) -> dict:
    """单因素方差分析（One-way ANOVA）：检验多组均值是否存在显著差异。"""
    groups = [np.asarray(g, dtype=float) for g in groups]
    f, p = stats.f_oneway(*groups)
    return {"F": float(f), "p_value": float(p), "significant": bool(p < alpha)}


def chi_square(table, alpha: float = 0.05) -> dict:
    """卡方独立性检验：检验两个分类变量是否独立。table 是列联表 (r, c)。"""
    table = np.asarray(table, dtype=float)
    chi2, p, dof, expected = stats.chi2_contingency(table)
    return {"chi2": float(chi2), "p_value": float(p), "dof": int(dof),
            "expected": expected, "significant": bool(p < alpha)}


def correlation(x, y, method: str = "pearson", alpha: float = 0.05) -> dict:
    """相关分析。method: pearson（线性）或 spearman（单调，抗离群/非线性）。"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if method == "pearson":
        r, p = stats.pearsonr(x, y)
    elif method == "spearman":
        r, p = stats.spearmanr(x, y)
    else:
        raise ValueError("method 只支持 pearson / spearman")
    return {"r": float(r), "p_value": float(p), "significant": bool(p < alpha)}


def normality_test(x, alpha: float = 0.05) -> dict:
    """正态性检验（Shapiro-Wilk）。p >= alpha 才可认为近似正态（t 检验/ANOVA 的前提）。"""
    x = np.asarray(x, dtype=float)
    stat, p = stats.shapiro(x)
    return {"statistic": float(stat), "p_value": float(p), "normal": bool(p >= alpha)}
