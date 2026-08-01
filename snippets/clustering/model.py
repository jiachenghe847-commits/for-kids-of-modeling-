import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score


def kmeans_cluster(X: np.ndarray, k: int, seed: int = 0) -> dict:
    """K-Means 聚类。X 为 (样本数, 特征数) 矩阵，k 为簇数。"""
    X = np.asarray(X, dtype=float)
    model = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = model.fit_predict(X)
    sil = silhouette_score(X, labels) if k > 1 and k < len(X) else float("nan")
    return {
        "labels": labels,
        "centers": model.cluster_centers_,
        "inertia": float(model.inertia_),
        "silhouette": float(sil),
    }


def hierarchical_cluster(X: np.ndarray, k: int, linkage: str = "ward") -> dict:
    """层次聚类（自底向上凝聚）。linkage 可选 ward/average/complete/single。"""
    X = np.asarray(X, dtype=float)
    model = AgglomerativeClustering(n_clusters=k, linkage=linkage)
    labels = model.fit_predict(X)
    sil = silhouette_score(X, labels) if k > 1 and k < len(X) else float("nan")
    return {"labels": labels, "silhouette": float(sil)}


def best_k_by_silhouette(X: np.ndarray, k_range=range(2, 8), seed: int = 0) -> dict:
    """扫描 k，用轮廓系数挑最优簇数，避免拍脑袋定 k。"""
    X = np.asarray(X, dtype=float)
    scores = {}
    for k in k_range:
        if k >= len(X):
            break
        labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(X)
        scores[k] = float(silhouette_score(X, labels))
    best_k = max(scores, key=scores.get)
    return {"scores": scores, "best_k": best_k}
