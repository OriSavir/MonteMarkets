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
    try:
        data = yf.download(ticker, period=f'{days}d', interval='1m', progress=False)
    except Exception as e:
        raise ValueError(f"Could not fetch the data for {ticker}")
    if data.empty:
        raise ValueError(f"Could not fetch the data for {ticker} (empty response)")
    data = data.reset_index()
    data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    return data

def fetch_most_recent_price_and_time(ticker):
    today = datetime.date.today()
    today_data = yf.download(ticker, period='1d', interval='1m', progress=False)
    today_data = today_data.reset_index()
    today_data.columns = [col[0] if isinstance(col, tuple) else col for col in today_data.columns]

    if today_data.empty or today not in today_data['Datetime'].dt.date.values:
        print("Non-trading day detected: using last available CLOSE price.")
        fallback_data = yf.download(ticker, period='5d', interval='1d', progress=False)
        fallback_data = fallback_data.reset_index()
        fallback_data.columns = [col[0] if isinstance(col, tuple) else col for col in fallback_data.columns]

        recent_close = fallback_data['Close'].iloc[-1]
        corresponding_date = fallback_data['Date'].iloc[-1]
        return float(recent_close), None, corresponding_date
    else:
        latest_row = today_data.iloc[-1]
        current_price = latest_row['Close']
        current_time = latest_row['Datetime'].time()
        return float(current_price), current_time, today



    

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
    data.set_index('Datetime',inplace=True)
    intraday = data.between_time(datetime.time(9, 31), datetime.time(16, 0))
    intraday = intraday.reset_index()
    data = data.reset_index()
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

def simulate_monte_carlo(
    scaled_vol_profile, 
    start_price, 
    real_log_returns=None, 
    num_simulations=1000, 
    random_seed=None
):
    if random_seed is not None:
        np.random.seed(random_seed)

    total_minutes = len(scaled_vol_profile)
    real_minutes  = len(real_log_returns) if real_log_returns is not None else 0
    sim_minutes   = total_minutes - real_minutes
    if sim_minutes < 0:
        raise ValueError("Too many real returns for the vol profile length")

    zeros = np.zeros((num_simulations, 1))

    if real_log_returns is not None and real_minutes > 0:
        real_block = np.tile(real_log_returns, (num_simulations, 1))
    else:
        real_block = np.zeros((num_simulations, 0))

    shocks = np.random.randn(num_simulations, sim_minutes)
    sim_block = shocks * scaled_vol_profile.values[-sim_minutes:,]

    all_returns = np.concatenate([zeros, real_block, sim_block], axis=1)

    cum_returns = np.cumsum(all_returns, axis=1)
    rel_prices  = np.exp(cum_returns)

    prices = start_price * rel_prices

    return prices



def get_confidence_intervals(prices, levels=[95, 99]):
    intervals = {}
    for level in levels:
        low = np.percentile(prices[:, -1], (100 - level) / 2)
        high = np.percentile(prices[:, -1], 100 - (100 - level) / 2)
        intervals[level] = (low, high)
    return intervals


def generate_simulation_data(ticker, num_simulations=1000, random_seed=None):
    """
    Gets data for a ticker, processes it, runs the Monte Carlo simulation, and returns
    the simulated price paths and confidence intervals for the close price.
    """
    try:
        minute_data = fetch_minute_data(ticker)
    except ValueError as e:
        raise ValueError(f"Error fetching data for {ticker}: {e}")
    minute_data = add_returns(minute_data)

    vol_profile = compute_intraday_volatility_profile(minute_data)

    daily_returns = minute_data.groupby('Date')['Log_Return'].sum()

    daily_volatility = forecast_daily_volatility(daily_returns)

    scaled_vol_profile = scale_volatility_profile(vol_profile, daily_volatility)
    
    start_price, current_time, start_date = fetch_most_recent_price_and_time(ticker)

    if current_time is not None:
        today_df = yf.download(ticker, period='1d', interval='1m', progress=False)
        today_df = today_df.reset_index()
        today_df.columns = [c[0] if isinstance(c, tuple) else c for c in today_df.columns]
        today_df['Time'] = today_df['Datetime'].dt.time
        today_df['Log_Return'] = np.log(today_df['Close']/today_df['Close'].shift(1))

        real_df = today_df[today_df['Time'] <= current_time].dropna(subset=['Log_Return'])
        real_log_returns = real_df['Log_Return'].values
    else:
        real_log_returns = None

    prices = simulate_monte_carlo(
        scaled_vol_profile,
        start_price,
        real_log_returns=real_log_returns,
        num_simulations=num_simulations,
        random_seed=random_seed
    )

    expected_prices = prices.mean(axis=0)
    intervals       = get_confidence_intervals(prices)

    return prices, expected_prices, intervals, start_date