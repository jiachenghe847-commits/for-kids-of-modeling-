from scipy.optimize import linprog


def solve_lp(c, A_ub, b_ub, bounds) -> dict:
    result = linprog(c=c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    return {"x": result.x, "objective": float(result.fun), "success": bool(result.success)}
