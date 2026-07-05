import numpy as np

_RANDOM_INDEX = {1: 0, 2: 0, 3: 0.58, 4: 0.9, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def ahp_weights(matrix: np.ndarray) -> dict:
    n = matrix.shape[0]
    eigvals, eigvecs = np.linalg.eig(matrix)
    max_idx = int(np.argmax(eigvals.real))
    lambda_max = eigvals[max_idx].real
    weights = eigvecs[:, max_idx].real
    weights = weights / weights.sum()

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = _RANDOM_INDEX.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0

    return {"weights": weights, "cr": float(cr), "consistent": bool(cr < 0.1)}
