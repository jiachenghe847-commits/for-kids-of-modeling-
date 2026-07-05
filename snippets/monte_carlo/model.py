import numpy as np


def estimate_by_sampling(sampler, n_trials: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    samples = np.array([sampler(rng) for _ in range(n_trials)])
    return {"mean": float(samples.mean()), "std": float(samples.std())}
