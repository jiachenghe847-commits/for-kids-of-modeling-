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


def confidence_interval(x, alpha: float = 0.05) -> dict:
    """均值的置信区间（t 分布，未知总体方差的小样本口径）。

    论文里报一个点估计而不给区间，评委没法判断这个数有多可靠。获奖论文的结果表
    普遍带 95% CI 一列——把这个函数的输出直接填进去即可。

    样本量小（n < 30）且明显偏态时 t 区间会失真，这种情况改用 bootstrap_ci。
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 2:
        raise ValueError("置信区间至少需要 2 个样本")
    mean = float(x.mean())
    sem = float(stats.sem(x, ddof=1))
    df = n - 1
    half = float(stats.t.ppf(1 - alpha / 2, df) * sem)
    return {"mean": mean, "ci_low": mean - half, "ci_high": mean + half,
            "half_width": half, "sem": sem, "n": int(n), "df": int(df),
            "confidence": 1 - alpha}


def coefficient_of_variation(x) -> dict:
    """变异系数 CV = 标准差 / 均值，用百分数表示，衡量相对离散程度。

    比标准差更适合跨量纲比较——「厚度的标准差 0.17 µm」说明不了什么，
    「CV = 2.8%」才能和别的量放在一起看。经验刻度：CV < 3% 重复性优秀，
    3%~5% 良好，5%~10% 基本可接受，> 10% 提示模型或数据处理有问题。

    均值接近 0 时 CV 没有意义（分母趋零会放大成任意大），此时返回的
    ``meaningful`` 为 False，不要往论文里填。
    """
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        raise ValueError("变异系数至少需要 2 个样本")
    mean = float(x.mean())
    std = float(x.std(ddof=1))
    meaningful = abs(mean) > 1e-12 and abs(mean) > std * 1e-3
    return {"cv_percent": float(std / mean * 100) if meaningful else float("nan"),
            "mean": mean, "std": std, "n": int(x.size), "meaningful": bool(meaningful)}


def bootstrap_ci(x, statistic=np.mean, n_resamples: int = 10000,
                 alpha: float = 0.05, seed: int | None = None) -> dict:
    """自助法置信区间（BCa 校正），不假设总体分布。

    适用场景：样本量小、分布明显非正态，或者要给**中位数、分位数、最大值**这类
    没有解析分布的统计量配区间——t 区间只管均值，这些量只能靠重采样。

    ``seed`` 一定要给，否则同一份数据两次运行结果不同，论文就不可复现了。
    """
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        raise ValueError("自助法至少需要 2 个样本")
    result = stats.bootstrap(
        (x,), statistic, n_resamples=n_resamples,
        confidence_level=1 - alpha, method="BCa",
        random_state=np.random.default_rng(seed),
    )
    return {"point": float(statistic(x)),
            "ci_low": float(result.confidence_interval.low),
            "ci_high": float(result.confidence_interval.high),
            "standard_error": float(result.standard_error),
            "n": int(x.size), "n_resamples": int(n_resamples),
            "confidence": 1 - alpha, "seed": seed}
