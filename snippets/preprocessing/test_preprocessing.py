import numpy as np
from .model import fill_missing, detect_outliers, standardize, normalize


def test_fill_missing_interpolate():
    x = np.array([1.0, np.nan, 3.0])
    result = fill_missing(x, strategy="interpolate")
    assert result["filled"][1] == 2.0
    assert result["n_filled"] == 1


def test_fill_missing_mean():
    x = np.array([2.0, np.nan, 4.0])
    result = fill_missing(x, strategy="mean")
    assert result["filled"][1] == 3.0


def test_detect_outliers_iqr_flags_extreme():
    x = np.array([10, 11, 12, 13, 100], dtype=float)
    result = detect_outliers(x, method="iqr")
    assert result["outliers"][-1]  # 100 是异常值
    assert result["n_outliers"] == 1


def test_standardize_zero_mean_unit_std():
    X = np.array([[1.0], [2.0], [3.0]])
    result = standardize(X)
    assert abs(result["scaled"].mean()) < 1e-9
    assert abs(result["scaled"].std() - 1.0) < 1e-9


def test_normalize_to_unit_range():
    X = np.array([[0.0], [5.0], [10.0]])
    result = normalize(X)
    assert result["scaled"].min() == 0.0
    assert result["scaled"].max() == 1.0
