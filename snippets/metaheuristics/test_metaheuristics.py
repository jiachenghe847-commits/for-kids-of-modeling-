import numpy as np
from .model import genetic_optimize, anneal_optimize, tsp_anneal


def _rastrigin(x):
    x = np.asarray(x)
    return 10 * len(x) + np.sum(x ** 2 - 10 * np.cos(2 * np.pi * x))


def test_ga_finds_rastrigin_global_min():
    # Rastrigin 全局最小在原点，值为 0
    result = genetic_optimize(_rastrigin, bounds=[(-5.12, 5.12)] * 2)
    assert result["objective"] < 1e-4
    assert np.allclose(result["x"], 0, atol=1e-2)


def test_anneal_finds_min():
    result = anneal_optimize(_rastrigin, bounds=[(-5.12, 5.12)] * 2)
    assert result["objective"] < 1e-2


def test_tsp_solves_square():
    # 单位正方形四个角，最优闭环路程 = 4
    coords = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=float)
    dist = np.linalg.norm(coords[:, None] - coords[None, :], axis=2)
    result = tsp_anneal(dist, iters=5000)
    assert abs(result["length"] - 4.0) < 1e-6
