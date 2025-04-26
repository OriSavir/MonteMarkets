import numpy as np
import pandas as pd
import yfinance as yf
from arch import arch_model
import datetime

# ---------------------------
# data fetching utilities
# ---------------------------

def fetch_minute_data(ticker, days=8):
    if days > 8:
        raise ValueError("Max number of days is 8 for minute data")
    if days < 1:
        raise ValueError("Min number of days is 1 for minute data")
    data = yf.download(ticker, period=f'{days}d', interval='1m', progress=False)
    data = data.reset_index()
    data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    return data

def fetch_most_recent_open(ticker):
    today = datetime.date.today()
    today_data = yf.download(ticker, period='1d', interval='1m', progress=False)
    today_data = today_data.reset_index()
    today_data.columns = [col[0] if isinstance(col, tuple) else col for col in today_data.columns]

    if today_data.empty or today not in today_data['Datetime'].dt.date.values:
        fallback_data = yf.download(ticker, period='5d', interval='1d', progress=False)
        fallback_data = fallback_data.reset_index()
        fallback_data.columns = [col[0] if isinstance(col, tuple) else col for col in fallback_data.columns]
        recent_open = fallback_data['Open'].iloc[-1]
        corresponding_date = fallback_data['Date'].iloc[-1]
    else:
        recent_open = today_data['Open'].iloc[0]
        corresponding_date = today

    if isinstance(corresponding_date, pd.Timestamp):
        corresponding_date = corresponding_date.date()

    return float(recent_open), corresponding_date

    

# ---------------------------
# preprocessing utilities
# ---------------------------

def add_returns(data):
    data['Return'] = data['Close'].pct_change()
    data['Log_Return'] = np.log(data['Close'] / data['Close'].shift(1))
    data['Date'] = data['Datetime'].dt.date
    data['Time'] = data['Datetime'].dt.time
    return data.dropna(subset=['Return', 'Log_Return'])

def compute_intraday_volatility_profile(data):
    return data.groupby('Time')['Log_Return'].std()

# ---------------------------
# GARCH modeling
# ---------------------------

def forecast_daily_volatility(daily_log_returns):
    am = arch_model(daily_log_returns * 100, vol='Garch', p=1, q=1, mean='Zero')
    res = am.fit(disp="off")
    forecast = res.forecast(horizon=1)
    sigma_forecast = np.sqrt(forecast.variance.values[-1, :][0]) / 100
    return sigma_forecast

def scale_volatility_profile(vol_profile, target_daily_volatility):
    implied_variance = np.sum(vol_profile**2)
    target_variance = target_daily_volatility**2
    scaling_factor = np.sqrt(target_variance / implied_variance)
    return vol_profile * scaling_factor

# ---------------------------
# The monte-carlo sim utility
# ---------------------------

def simulate_monte_carlo(scaled_vol_profile, start_price, num_simulations=1000, random_seed=None):
    if random_seed is not None:
        np.random.seed(random_seed)
    
    num_minutes = len(scaled_vol_profile)
    random_shocks = np.random.randn(num_simulations, num_minutes)
    returns = random_shocks * scaled_vol_profile.values
    cum_returns = np.cumsum(returns, axis=1)
    relative_prices = np.exp(cum_returns)
    prices = start_price * relative_prices
    return prices

def get_confidence_intervals(prices, levels=[95, 99]):
    intervals = {}
    for level in levels:
        low = np.percentile(prices[:, -1], (100 - level) / 2)
        high = np.percentile(prices[:, -1], 100 - (100 - level) / 2)
        intervals[f"{level}%"] = (low, high)
    return intervals


def generate_simulation_data(ticker, num_simulations=1000, random_seed=None):
    """
    Gets data for a ticker, processes it, runs the Monte Carlo simulation, and returns
    the simulated price paths and confidence intervals for the close price.
    """
    minute_data = fetch_minute_data(ticker)
    minute_data = add_returns(minute_data)

    vol_profile = compute_intraday_volatility_profile(minute_data)

    daily_returns = minute_data.groupby('Date')['Log_Return'].sum()

    daily_volatility = forecast_daily_volatility(daily_returns)

    scaled_vol_profile = scale_volatility_profile(vol_profile, daily_volatility)

    start_price, recent_open_date = fetch_most_recent_open(ticker)

    prices = simulate_monte_carlo(
        scaled_vol_profile, 
        start_price, 
        num_simulations=num_simulations, 
        random_seed=random_seed
    )

    intervals = get_confidence_intervals(prices)

    return prices, intervals, recent_open_date