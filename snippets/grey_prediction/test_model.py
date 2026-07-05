import numpy as np
from model import gm11_forecast


def test_gm11_forecast_reproduces_training_length_and_extends():
    series = np.array([100, 105, 112, 120, 130], dtype=float)
    result = gm11_forecast(series, steps=2)
    assert len(result["forecast"]) == len(series) + 2
    # 拟合值应该接近原始序列前几个点（GM(1,1) 对平稳增长序列拟合较好）
    assert abs(result["forecast"][1] - series[1]) / series[1] < 0.1
