import numpy as np
import pandas as pd
import yfinance as yf
from arch import arch_model
import datetime
import pandas_market_calendars as mcal
import pytz

# set the timezone
TZ = pytz.timezone('America/New_York')

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
    timezone = datetime.datetime.now(TZ)
    today = timezone.date()
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
    
def get_next_trading_day(start_date):
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=start_date, end_date=start_date + datetime.timedelta(days=7))

    future_trading_days = schedule.index.to_list()
    for trading_day in future_trading_days:
        if trading_day.date() > start_date:
            return trading_day.date()
    
    return start_date + datetime.timedelta(days=1)




    

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

    # Get the total number of minutes to simulate
    total_minutes = len(scaled_vol_profile)
    
    # If we have real returns, we'll use them for the beginning part
    if real_log_returns is not None and len(real_log_returns) > 0:
        real_minutes = len(real_log_returns)
        # We'll simulate the remaining minutes
        sim_minutes = total_minutes
    else:
        real_minutes = 0
        sim_minutes = total_minutes
    
    # Generate random shocks for the simulated part
    shocks = np.random.randn(num_simulations, sim_minutes)
    
    # Scale the shocks by the volatility profile
    sim_returns = shocks * scaled_vol_profile.values
    
    # Create the full array of returns
    all_returns = sim_returns
    
    # Calculate cumulative returns
    cum_returns = np.cumsum(all_returns, axis=1)
    
    # Convert to prices
    prices = start_price * np.exp(cum_returns)
    
    return prices




def get_confidence_intervals(prices, level=95):
    low = np.percentile(prices[:, -1], (100 - level) / 2)
    high = np.percentile(prices[:, -1], 100 - (100 - level) / 2)
    interval = (low, high)
    return interval


def generate_simulation_data(ticker, num_simulations=1000, random_seed=None):
    """
    Gets data for a ticker, processes it, runs the Monte Carlo simulation, and returns
    a JSON-serializable dict
    """
    try:
        minute_data = fetch_minute_data(ticker)
    except ValueError as e:
        raise ValueError(f"Error fetching data for {ticker}: {e}")

    # Process data and compute volatility profile
    minute_data = add_returns(minute_data)
    vol_profile = compute_intraday_volatility_profile(minute_data)
    daily_returns = minute_data.groupby('Date')['Log_Return'].sum()
    daily_volatility = forecast_daily_volatility(daily_returns)
    scaled_vol_profile = scale_volatility_profile(vol_profile, daily_volatility)

    # Get current price and time information
    current_price, current_time, current_date = fetch_most_recent_price_and_time(ticker)
    
    # Define market hours in EST
    market_open = datetime.time(9, 30, tzinfo=TZ)
    market_close = datetime.time(16, 0, tzinfo=TZ)
    
    # Determine if we're in trading hours
    is_trading_hours = (
        current_time is not None and 
        current_time >= market_open and 
        current_time <= market_close
    )
    
    if is_trading_hours:
        # During trading hours
        sim_date = current_date
        
        # Get today's minute data
        today_df = yf.download(ticker, period='1d', interval='1m', progress=False)
        today_df = today_df.reset_index()
        today_df.columns = [c[0] if isinstance(c, tuple) else c for c in today_df.columns]
        
        # Get the opening price - this will be the same for all simulations
        opening_price = today_df['Open'].iloc[0]
        
        # Get real data up to current time
        today_df['Time'] = today_df['Datetime'].dt.time
        real_data = today_df[today_df['Time'] <= current_time]
        
        if len(real_data) > 0:
            # Get real returns
            real_data['Log_Return'] = np.log(real_data['Close'] / real_data['Close'].shift(1))
            real_log_returns = real_data['Log_Return'].dropna().values
            
            # Current price to start simulations from
            start_price = real_data['Close'].iloc[-1]
        else:
            real_log_returns = None
            start_price = opening_price
        
        # Create a subset of the volatility profile for times after current time
        future_vol = scaled_vol_profile[scaled_vol_profile.index > current_time]
        
        # Run simulation for future prices
        if len(future_vol) > 0:
            future_prices = simulate_monte_carlo(
                future_vol,
                start_price,
                real_log_returns=None,
                num_simulations=num_simulations,
                random_seed=random_seed
            )
        else:
            # No future times to simulate
            future_prices = np.full((num_simulations, 1), start_price)
        
        # Now we need to create the full price array
        # First, initialize with zeros
        full_prices = np.zeros((num_simulations, len(scaled_vol_profile)))
        
        # For each time point in the full day
        for i, time_point in enumerate(scaled_vol_profile.index):
            if time_point <= current_time:
                # For past times, use the real price for all simulations
                if len(real_data[real_data['Time'] == time_point]) > 0:
                    price = real_data[real_data['Time'] == time_point]['Close'].iloc[0]
                else:
                    # If we don't have data for this exact time, use the closest earlier time
                    earlier_data = real_data[real_data['Time'] <= time_point]
                    if len(earlier_data) > 0:
                        price = earlier_data['Close'].iloc[-1]
                    else:
                        # If no earlier time, use opening price
                        price = opening_price
                
                # Set the same price for all simulations
                full_prices[:, i] = price
            else:
                # For future times, use the simulated prices
                future_idx = sum(1 for t in future_vol.index if t <= time_point) - 1
                if future_idx >= 0 and future_idx < future_prices.shape[1]:
                    full_prices[:, i] = future_prices[:, future_idx]
        
        # Use the full prices array
        prices = full_prices
        
    else:
        # Outside trading hours - simulate next trading day
        sim_date = get_next_trading_day(current_date)
        
        # All simulations start from the same price
        opening_price = current_price
        
        # Run the simulation
        prices = simulate_monte_carlo(
            scaled_vol_profile,
            opening_price,
            real_log_returns=None,
            num_simulations=num_simulations,
            random_seed=random_seed
        )
        
        # Explicitly set the first price to be the opening price for all simulations
        prices[:, 0] = opening_price
    
    # Verify that all simulations have the same opening price
    assert np.all(prices[:, 0] == prices[0, 0]), "Opening prices are not the same across all simulations!"
    
    # Calculate statistics
    expected_prices = prices.mean(axis=0).round(2)
    intervals = get_confidence_intervals(prices)
    intervals = tuple(round(i, 2) for i in intervals)
    prices = prices.round(2)
    final_prices = prices[:, -1]

    return {
        "prices": prices.tolist(),
        "expected_prices": expected_prices.tolist(),
        "intervals": intervals,
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