import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline


def _fit_report(model, X, y):
    model.fit(X, y)
    acc = float((model.predict(X) == y).mean())
    return {"predict": model.predict, "accuracy": acc, "model": model}


def lda_classify(X, y) -> dict:
    """Fisher 线性判别分析（LDA）。有标签样本、类别近似正态、线性可分时首选，可解释性好。"""
    X = np.asarray(X, dtype=float)
    return _fit_report(make_pipeline(StandardScaler(), LinearDiscriminantAnalysis()), X, np.asarray(y))


def svm_classify(X, y, kernel: str = "rbf", C: float = 1.0) -> dict:
    """支持向量机分类。中小样本、边界非线性时强；kernel 可选 linear/rbf/poly。已内置标准化。"""
    X = np.asarray(X, dtype=float)
    return _fit_report(make_pipeline(StandardScaler(), SVC(kernel=kernel, C=C)), X, np.asarray(y))


def tree_classify(X, y, max_depth: int = None, seed: int = 0) -> dict:
    """决策树分类。可解释性最好（能画出规则），但易过拟合，用 max_depth 限制深度。"""
    X = np.asarray(X, dtype=float)
    model = DecisionTreeClassifier(max_depth=max_depth, random_state=seed)
    out = _fit_report(model, X, np.asarray(y))
    out["feature_importance"] = model.feature_importances_
    return out


def random_forest_classify(X, y, n_estimators: int = 100, seed: int = 0) -> dict:
    """随机森林分类。综合多棵树，精度稳、抗过拟合，还能给特征重要性；解释性弱于单棵树。"""
    X = np.asarray(X, dtype=float)
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=seed)
    out = _fit_report(model, X, np.asarray(y))
    out["feature_importance"] = model.feature_importances_
    return out


def naive_bayes_classify(X, y) -> dict:
    """朴素贝叶斯（高斯型）。特征近似条件独立时又快又稳，小样本表现好，可输出类别概率。"""
    X = np.asarray(X, dtype=float)
    model = GaussianNB()
    out = _fit_report(model, X, np.asarray(y))
    out["predict_proba"] = model.predict_proba
    return out


def logistic_classify(X, y, max_iter: int = 1000) -> dict:
    """Logistic 回归（二分类/多分类）。可解释性强：系数反映各因素对"发生概率"的影响方向与大小。

    返回 coef（各特征系数，已标准化尺度）、odds_ratio（优势比 e^coef）与概率预测函数。
    """
    X = np.asarray(X, dtype=float)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=max_iter))
    out = _fit_report(model, X, np.asarray(y))
    lr = model.named_steps["logisticregression"]
    out["coef"] = lr.coef_
    out["intercept"] = lr.intercept_
    out["odds_ratio"] = np.exp(lr.coef_)
    out["predict_proba"] = model.predict_proba
    return out
