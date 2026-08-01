import numpy as np
from scipy.optimize import differential_evolution, dual_annealing


def genetic_optimize(func, bounds, seed: int = 0, maxiter: int = 200) -> dict:
    """遗传/差分进化算法求全局最小值（scipy differential_evolution）。

    func: 目标函数 f(x)->标量，x 为参数向量；求最大化就返回 -f(x)。
    bounds: 每个变量的 (low, high) 列表，如 [(-5, 5), (-5, 5)]。
    """
    result = differential_evolution(func, bounds, seed=seed, maxiter=maxiter, polish=True)
    return {"x": result.x, "objective": float(result.fun), "success": bool(result.success),
            "nit": int(result.nit)}


def anneal_optimize(func, bounds, seed: int = 0, maxiter: int = 1000) -> dict:
    """模拟退火求全局最小值（scipy dual_annealing）。适合多峰、离散化后的连续松弛问题。"""
    result = dual_annealing(func, bounds, seed=seed, maxiter=maxiter)
    return {"x": result.x, "objective": float(result.fun), "success": bool(result.success)}


def tsp_anneal(dist: np.ndarray, seed: int = 0, iters: int = 20000, T0: float = 100.0) -> dict:
    """用模拟退火解旅行商问题（TSP，组合优化的经典代表）。

    dist: 对称距离矩阵 (n, n)。返回访问顺序与总路程（闭环，回到起点）。
    """
    rng = np.random.default_rng(seed)
    n = len(dist)
    route = np.arange(n)

    def tour_len(r):
        return sum(dist[r[i], r[(i + 1) % n]] for i in range(n))

    best = route.copy()
    best_len = cur_len = tour_len(route)
    T = T0
    for _ in range(iters):
        i, j = sorted(rng.integers(0, n, 2))
        if i == j:
            continue
        cand = route.copy()
        cand[i:j + 1] = cand[i:j + 1][::-1]   # 2-opt 反转
        cand_len = tour_len(cand)
        if cand_len < cur_len or rng.random() < np.exp((cur_len - cand_len) / T):
            route, cur_len = cand, cand_len
            if cur_len < best_len:
                best, best_len = route.copy(), cur_len
        T *= 0.9995
    return {"route": best, "length": float(best_len)}
