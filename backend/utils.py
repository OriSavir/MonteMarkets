import numpy as np
import pandas as pd
import yfinance as yf
from arch import arch_model
import datetime
import pandas_market_calendars as mcal
import pytz

TZ = pytz.timezone('America/New_York')

# -------------------------------
# 1. Fetch & preprocess intraday
# -------------------------------
def _fetch_minute_data(ticker, days=5):
    now = datetime.datetime.now(TZ)
    data = yf.download(ticker, period=f'{days}d', interval='1m', progress=False)
    if data.empty:
        raise ValueError("No intraday data returned")
    data = data.reset_index()
    data['Datetime'] = data['Datetime'].dt.tz_convert(TZ)
    data['Return'] = data['Close'].pct_change()
    data['Log_Return'] = np.log(data['Close'] / data['Close'].shift(1))
    data['Date'] = data['Datetime'].dt.date
    data['Time'] = data['Datetime'].dt.time
    data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    data.dropna(subset=['Return', 'Log_Return'], inplace=True)
    data = data.set_index('Datetime')
    data = data.between_time("09:30", "16:00")
    data = data.reset_index()
    return data, now.date(), now.time()

# ---------------------------------
# 2. Filter only trading hour data
# ---------------------------------
def _filter_trading_hours(data):
    data = data.set_index('Datetime')
    data = data.between_time("09:30", "16:00")
    data = data.reset_index()

# --------------------------------------
# 3. Compute volatility profile by minute
# --------------------------------------
def _compute_volatility_profile(data):
    if data.empty:
        raise ValueError("No data available for volatility profile calculation")
    grouped = data.groupby('Time')['Log_Return'].std()
    return grouped

# -------------------------------------
# 4. Scale volatility using GARCH model
# -------------------------------------
def _scale_vol_profile(data, vol_profile, current_date, current_time):
    # Choose data to fit GARCH based on time
    if current_time < datetime.time(9, 30) or current_time > datetime.time(16, 0):
        fit_data = data[data['Date'] < current_date]
    else:
        fit_data = data[data['Date'] < current_date]  # Only use prior full days

    daily_returns = fit_data.groupby('Date')['Log_Return'].sum()
    model = arch_model(daily_returns * 100, vol='Garch', p=1, q=1, mean='Zero')
    res = model.fit(disp='off')
    daily_vol = np.sqrt(res.forecast(horizon=1).variance.values[-1, :][0]) / 100

    implied_var = np.sum(vol_profile**2)
    scale_factor = daily_vol / np.sqrt(implied_var)
    return vol_profile * scale_factor

# -------------------------------------
# 5. Determine next trading day
# -------------------------------------
def get_next_trading_day(start_date):
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_date, end_date=start_date + datetime.timedelta(days=7))
    for d in schedule.index:
        if d.date() > start_date:
            return d.date()
    return start_date + datetime.timedelta(days=1)

# -------------------------------------
# 6. Simulate price paths
# -------------------------------------
def _simulate_paths(start_price, vol_profile, num_simulations, seed=None):
    if seed is not None:
        np.random.seed(seed)
    shocks = np.random.randn(num_simulations, len(vol_profile))
    returns = shocks * vol_profile.values
    cum_returns = np.cumsum(returns, axis=1)
    prices = start_price * np.exp(cum_returns)
    return prices

def _simulate_with_overlap(data_today, vol_profile, num_simulations, seed=None):
    last_time = data_today['Time'].max()
    real_returns = data_today['Log_Return'].dropna().values
    base_price = data_today['Close'].iloc[-1]

    future_times = [t for t in vol_profile.index if t > last_time]
    future_vol = vol_profile[vol_profile.index > last_time]
    future_sim = _simulate_paths(base_price, future_vol, num_simulations, seed)

    all_prices = np.zeros((num_simulations, len(vol_profile)))
    for i, t in enumerate(vol_profile.index):
        if t <= last_time:
            price = data_today[data_today['Time'] == t]['Close']
            val = price.iloc[0] if not price.empty else base_price
            all_prices[:, i] = val
        else:
            idx = list(future_vol.index).index(t)
            all_prices[:, i] = future_sim[:, idx]
    return all_prices

# -------------------------------------
# 7. Main Entry Point
# -------------------------------------
def generate_simulation_data(ticker, num_simulations=1000, random_seed=None):
    data, current_date, current_time = _fetch_minute_data(ticker)
    #data = _filter_trading_hours(data)
    vol_profile = _compute_volatility_profile(data)
    scaled_vol_profile = _scale_vol_profile(data, vol_profile, current_date, current_time)

    is_trading_time = datetime.time(9, 30) <= current_time <= datetime.time(16, 0)
    sim_date = current_date if is_trading_time else get_next_trading_day(current_date)

    if is_trading_time:
        today_data = data[data['Date'] == current_date]
        prices = _simulate_with_overlap(today_data, scaled_vol_profile, num_simulations, random_seed)
    else:
        last_close = data[data['Date'] == data['Date'].max()]['Close'].iloc[-1]
        prices = _simulate_paths(last_close, scaled_vol_profile, num_simulations, random_seed)
        prices[:, 0] = last_close

    expected_prices = prices.mean(axis=0).round(2)
    final_prices = prices[:, -1].round(2)
    interval = np.percentile(final_prices, [2.5, 97.5]).round(2)

    return {
        "prices": prices.round(2).tolist(),
        "expected_prices": expected_prices.tolist(),
        "intervals": tuple(interval),
        "recent_open_date": sim_date,
        "final_prices": final_prices.tolist()
    }




def clean_numpy(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, dict):
        return {k: clean_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_numpy(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(clean_numpy(v) for v in obj)
    else:
        return obj