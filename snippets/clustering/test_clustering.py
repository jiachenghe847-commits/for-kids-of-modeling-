import numpy as np
from .model import kmeans_cluster, hierarchical_cluster, best_k_by_silhouette


def _three_blobs():
    rng = np.random.default_rng(0)
    a = rng.normal([0, 0], 0.3, (20, 2))
    b = rng.normal([5, 5], 0.3, (20, 2))
    c = rng.normal([0, 5], 0.3, (20, 2))
    return np.vstack([a, b, c])


def test_kmeans_separates_three_blobs():
    X = _three_blobs()
    result = kmeans_cluster(X, k=3)
    assert len(set(result["labels"].tolist())) == 3
    assert result["silhouette"] > 0.7  # 三团分得很开，轮廓系数应该高


def test_hierarchical_matches_block_structure():
    X = _three_blobs()
    result = hierarchical_cluster(X, k=3)
    # 每一团 20 个点应聚成大小相近的三簇
    _, counts = np.unique(result["labels"], return_counts=True)
    assert sorted(counts.tolist()) == [20, 20, 20]


def test_best_k_recovers_three():
    X = _three_blobs()
    result = best_k_by_silhouette(X, k_range=range(2, 6))
    assert result["best_k"] == 3
