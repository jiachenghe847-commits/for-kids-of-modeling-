import numpy as np
from .model import (
    solve_lexicographic_lp,
    solve_lexicographic_milp,
    solve_lp,
    solve_milp,
    solve_nlp,
    solve_multi_objective,
)


def test_solve_lp_known_optimum():
    # 最小化 -x - 2y （即最大化 x + 2y），约束 x + y <= 4, x <= 3, x,y >= 0
    result = solve_lp(
        c=[-1, -2],
        A_ub=[[1, 1], [1, 0]],
        b_ub=[4, 3],
        bounds=[(0, None), (0, None)],
    )
    assert result["success"] is True
    assert abs(result["objective"] - (-8)) < 1e-6


def test_solve_milp_integer_optimum():
    # 最大化 x + y，约束 x + 2y <= 4, 3x + 2y <= 6，x,y 非负整数
    # 可行整数点里 x+y 最大为 2（如 (2,0)/(0,2)/(1,1)），(3,0)/(0,3) 均越界
    result = solve_milp(
        c=[-1, -1],
        A_ub=[[1, 2], [3, 2]],
        b_ub=[4, 6],
        bounds=[(0, None), (0, None)],
        integrality=[1, 1],
    )
    assert result["success"] is True
    assert np.allclose(result["x"], np.round(result["x"]))  # 解确为整数
    assert abs(result["objective"] - (-2)) < 1e-6           # x+y 最大为 2


def test_solve_nlp_constrained_min():
    # 最小化 (x-2)^2 + (y-3)^2，无约束 -> 最优 (2,3)，目标 0
    result = solve_nlp(lambda v: (v[0] - 2) ** 2 + (v[1] - 3) ** 2, x0=[0, 0])
    assert result["success"] is True
    assert np.allclose(result["x"], [2, 3], atol=1e-4)
    assert result["objective"] < 1e-6


def test_multi_objective_compromise_between_ideals():
    # 两个冲突目标：目标1 最小化 -x（想 x 大），目标2 最小化 -y（想 y 大），约束 x+y<=4
    A_ub, b_ub = [[1, 1]], [4]
    bounds = [(0, None), (0, None)]
    result = solve_multi_objective(
        objectives=[[-1, 0], [0, -1]],
        weights=[0.5, 0.5],
        A_ub=A_ub, b_ub=b_ub, bounds=bounds,
    )
    assert result["success"] is True
    # 各自单独最优都是 -4（把 4 全给自己）
    assert all(abs(v - (-4)) < 1e-6 for v in result["ideals"])
    # 折中解下 x+y 仍应用满约束
    assert abs(sum(result["x"]) - 4) < 1e-6


def test_multi_objective_weight_shifts_solution():
    # 权重偏向第一个目标时，x 应该拿到更多
    A_ub, b_ub = [[1, 1]], [4]
    bounds = [(0, None), (0, None)]
    r = solve_multi_objective([[-1, 0], [0, -1]], [0.9, 0.1], A_ub, b_ub, bounds)
    assert r["x"][0] > r["x"][1]


def test_lexicographic_lp_preserves_first_priority():
    # First maximize x, then maximize y. A weighted compromise can sacrifice x;
    # the staged solver must keep the first objective at its exact optimum.
    result = solve_lexicographic_lp(
        objectives=[[-1, 0], [0, -1]],
        A_ub=[[1, 1]],
        b_ub=[4],
        bounds=[(0, None), (0, None)],
    )
    assert result["success"] and result["optimality_proven"]
    assert np.allclose(result["x"], [4, 0])
    assert result["objective_values"] == [-4.0, 0.0]
    assert all(stage["optimality_proven"] for stage in result["stages"])


def test_lexicographic_milp_keeps_integer_priority_and_status():
    result = solve_lexicographic_milp(
        objectives=[[-1, 0], [0, -1]],
        A_ub=[[1, 1]],
        b_ub=[4],
        bounds=[(0, 4), (0, 4)],
        integrality=[1, 1],
    )
    assert result["success"] and result["optimality_proven"]
    assert np.allclose(result["x"], [4, 0])
    assert result["stages"][0]["status"] == 0
    assert result["stages"][0]["mip_gap"] == 0.0


def test_solver_metadata_does_not_call_a_time_limited_run_optimal():
    result = solve_milp(
        c=[-1, -1], A_ub=[[1, 1]], b_ub=[4],
        bounds=[(0, 4), (0, 4)], integrality=[1, 1],
        options={"time_limit": 0.0},
    )
    assert result["success"] is False
    assert result["optimality_proven"] is False
    assert result["status"] != 0
