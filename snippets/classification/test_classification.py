import numpy as np
from .model import (lda_classify, svm_classify, tree_classify, random_forest_classify,
                    naive_bayes_classify, logistic_classify)


def _two_classes():
    rng = np.random.default_rng(0)
    a = rng.normal([0, 0], 0.6, (60, 2))
    b = rng.normal([4, 4], 0.6, (60, 2))
    X = np.vstack([a, b])
    y = np.array([0] * 60 + [1] * 60)
    return X, y


def test_lda_separates():
    X, y = _two_classes()
    result = lda_classify(X, y)
    assert result["accuracy"] > 0.95
    assert result["predict"](X[:3]).shape == (3,)


def test_svm_separates():
    X, y = _two_classes()
    result = svm_classify(X, y, kernel="rbf")
    assert result["accuracy"] > 0.95


def test_tree_gives_feature_importance():
    X, y = _two_classes()
    result = tree_classify(X, y, max_depth=3)
    assert result["accuracy"] > 0.9
    assert len(result["feature_importance"]) == 2
    assert abs(result["feature_importance"].sum() - 1.0) < 1e-6


def test_random_forest_accurate():
    X, y = _two_classes()
    result = random_forest_classify(X, y)
    assert result["accuracy"] > 0.95
    assert len(result["feature_importance"]) == 2


def test_naive_bayes_separates_and_gives_proba():
    X, y = _two_classes()
    result = naive_bayes_classify(X, y)
    assert result["accuracy"] > 0.95
    proba = result["predict_proba"](X[:5])
    assert proba.shape == (5, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)


def test_logistic_gives_coef_and_odds_ratio():
    X, y = _two_classes()
    result = logistic_classify(X, y)
    assert result["accuracy"] > 0.95
    assert result["coef"].shape == (1, 2)
    # 两个特征都随类别升高而增大 -> 系数为正、优势比 > 1
    assert (result["coef"] > 0).all()
    assert (result["odds_ratio"] > 1).all()
