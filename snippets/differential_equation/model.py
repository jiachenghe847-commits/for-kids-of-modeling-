import numpy as np
from scipy.integrate import solve_ivp


def solve_ode(func, y0, t_span, t_eval=None, args=(), method: str = "RK45") -> dict:
    """常微分方程（组）数值求解，封装 scipy 的 solve_ivp。

    func: 右端函数 f(t, y, *args)，返回 dy/dt（标量或数组）。
    y0: 初值（标量或数组）。
    t_span: (t0, t_end)。
    t_eval: 想要输出解的时间点数组；None 则由求解器自适应给点。
    args: 传给 func 的额外参数（如模型系数）。
    """
    y0 = np.atleast_1d(np.asarray(y0, dtype=float))
    if t_eval is None:
        t_eval = np.linspace(t_span[0], t_span[1], 200)
    sol = solve_ivp(func, t_span, y0, t_eval=t_eval, args=args, method=method, dense_output=True)
    return {"t": sol.t, "y": sol.y, "success": bool(sol.success), "sol": sol}


def sir_model(beta: float, gamma: float, S0: float, I0: float, R0: float,
              t_end: float = 160, n: int = 200) -> dict:
    """经典 SIR 传染病模型示例（传染病/舆情传播类题目常用）。

    beta: 传染率；gamma: 恢复率；S0/I0/R0: 初始易感/感染/恢复人数（比例或绝对数）。
    """
    N = S0 + I0 + R0

    def rhs(t, y):
        S, I, R = y
        dS = -beta * S * I / N
        dI = beta * S * I / N - gamma * I
        dR = gamma * I
        return [dS, dI, dR]

    out = solve_ode(rhs, [S0, I0, R0], (0, t_end), t_eval=np.linspace(0, t_end, n))
    out["labels"] = ["S", "I", "R"]
    return out
