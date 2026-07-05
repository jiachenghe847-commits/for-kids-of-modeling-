from model import estimate_by_sampling


def test_estimate_by_sampling_converges_on_known_distribution():
    import numpy as np

    def sampler(rng):
        return rng.normal(loc=5.0, scale=1.0)

    result = estimate_by_sampling(sampler, n_trials=20000, seed=0)
    assert abs(result["mean"] - 5.0) < 0.1
