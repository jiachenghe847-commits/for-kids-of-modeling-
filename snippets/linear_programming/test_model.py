from model import solve_lp


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
