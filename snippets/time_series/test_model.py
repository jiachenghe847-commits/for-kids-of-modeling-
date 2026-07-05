import numpy as np
from model import arima_forecast


def test_arima_forecast_returns_requested_steps():
    rng = np.random.default_rng(0)
    series = np.cumsum(rng.normal(0, 1, size=50)) + 100
    result = arima_forecast(series, order=(1, 1, 0), steps=5)
    assert len(result["forecast"]) == 5
    assert isinstance(result["aic"], float)
