import numpy as np
from .model import gm11_forecast, grey_relation


def test_gm11_forecast_reproduces_training_length_and_extends():
    series = np.array([100, 105, 112, 120, 130], dtype=float)
    result = gm11_forecast(series, steps=2)
    assert len(result["forecast"]) == len(series) + 2
    # 拟合值应该接近原始序列前几个点（GM(1,1) 对平稳增长序列拟合较好）
    assert abs(result["forecast"][1] - series[1]) / series[1] < 0.1


def test_grey_relation_ranks_closest_to_reference():
    # 参考序列 [10,10,10]；对象1接近，对象2偏离 -> 对象1关联度更高、排名第1
    reference = np.array([10.0, 10.0, 10.0])
    comparisons = np.array([
        [9.5, 10.2, 9.8],   # 接近
        [3.0, 18.0, 2.0],   # 偏离
    ])
    result = grey_relation(reference, comparisons)
    assert result["grade"][0] > result["grade"][1]
    assert result["rank"][0] == 1
