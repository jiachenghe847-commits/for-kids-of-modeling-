import numpy as np
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def bp_regress(X, y, hidden=(16, 8), max_iter: int = 2000, seed: int = 0) -> dict:
    """BP 神经网络回归/预测。X: (n, 特征数)，y: (n,) 连续目标。

    返回训练好的 predict 函数、训练集 RMSE、R²。hidden 是隐藏层结构。
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    model = make_pipeline(
        StandardScaler(),
        MLPRegressor(hidden_layer_sizes=hidden, max_iter=max_iter, random_state=seed),
    )
    model.fit(X, y)
    pred = model.predict(X)
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    rmse = float(np.sqrt(np.mean((y - pred) ** 2)))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 1.0
    return {"predict": model.predict, "rmse": rmse, "r2": r2, "model": model}


def bp_classify(X, y, hidden=(16, 8), max_iter: int = 2000, seed: int = 0) -> dict:
    """BP 神经网络分类。X: (n, 特征数)，y: (n,) 类别标签。返回 predict 函数与训练集准确率。"""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y)
    model = make_pipeline(
        StandardScaler(),
        MLPClassifier(hidden_layer_sizes=hidden, max_iter=max_iter, random_state=seed),
    )
    model.fit(X, y)
    acc = float((model.predict(X) == y).mean())
    return {"predict": model.predict, "accuracy": acc, "model": model}
