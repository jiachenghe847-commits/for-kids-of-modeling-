import numpy as np
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.cross_decomposition import CCA
from sklearn.preprocessing import StandardScaler


def pca_reduce(X: np.ndarray, n_components=None, standardize: bool = True) -> dict:
    """主成分分析降维。

    X: (样本数, 特征数)。
    n_components: 保留主成分数；传 float(如 0.9) 表示保留累计方差达 90% 的主成分；None 保留全部。
    standardize: 指标量纲不同时务必 True（先 Z-score 标准化）。
    """
    X = np.asarray(X, dtype=float)
    if standardize:
        X = StandardScaler().fit_transform(X)
    model = PCA(n_components=n_components)
    transformed = model.fit_transform(X)
    return {
        "transformed": transformed,
        "components": model.components_,
        "explained_ratio": model.explained_variance_ratio_,
        "cumulative_ratio": np.cumsum(model.explained_variance_ratio_),
        "n_components": model.n_components_,
    }


def pca_composite_score(X: np.ndarray, threshold: float = 0.85) -> dict:
    """用 PCA 做综合评价打分：以各主成分方差贡献率为权重加权求综合得分。

    返回每个样本的综合得分与排名（得分越高越靠前）。
    """
    X = np.asarray(X, dtype=float)
    Xs = StandardScaler().fit_transform(X)
    model = PCA(n_components=threshold)
    scores_pc = model.fit_transform(Xs)
    weights = model.explained_variance_ratio_ / model.explained_variance_ratio_.sum()
    composite = scores_pc @ weights
    rank = (-composite).argsort().argsort() + 1
    return {
        "score": composite,
        "rank": rank,
        "weights": weights,
        "n_components": model.n_components_,
    }


def factor_analysis(X: np.ndarray, n_factors: int, standardize: bool = True) -> dict:
    """因子分析：把观测指标解释为少数几个「潜在公共因子」的线性组合。

    与 PCA 的区别：PCA 是纯粹的方差压缩（成分是指标的线性组合）；
    因子分析假设存在不可观测的潜在因子驱动指标变化，更适合"提炼隐含维度"（如满意度、能力）。
    """
    X = np.asarray(X, dtype=float)
    if standardize:
        X = StandardScaler().fit_transform(X)
    model = FactorAnalysis(n_components=n_factors, random_state=0)
    scores = model.fit_transform(X)
    loadings = model.components_          # (n_factors, n_features) 因子载荷
    communality = (loadings ** 2).sum(axis=0)   # 各指标的共同度
    return {"scores": scores, "loadings": loadings, "communality": communality,
            "noise_variance": model.noise_variance_}


def canonical_correlation(X: np.ndarray, Y: np.ndarray, n_components: int = 1) -> dict:
    """典型相关分析（CCA）：研究两组变量整体之间的相关性。

    X: 第一组变量 (n, p)，Y: 第二组变量 (n, q)。
    典型场景：一组经济指标 vs 一组环境指标，问"这两个方面整体相关吗"。
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    model = CCA(n_components=n_components)
    U, V = model.fit_transform(X, Y)
    U = np.atleast_2d(U.T).T if U.ndim > 1 else U.reshape(-1, 1)
    V = np.atleast_2d(V.T).T if V.ndim > 1 else V.reshape(-1, 1)
    corrs = [float(np.corrcoef(U[:, i], V[:, i])[0, 1]) for i in range(U.shape[1])]
    return {"correlations": corrs, "U": U, "V": V,
            "x_weights": model.x_weights_, "y_weights": model.y_weights_}
