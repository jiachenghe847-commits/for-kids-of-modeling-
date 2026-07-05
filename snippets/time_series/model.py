import numpy as np
from statsmodels.tsa.arima.model import ARIMA


def arima_forecast(series: np.ndarray, order: tuple, steps: int) -> dict:
    fitted = ARIMA(np.asarray(series, dtype=float), order=order).fit()
    forecast = fitted.forecast(steps=steps)
    return {"forecast": np.asarray(forecast), "aic": float(fitted.aic)}
