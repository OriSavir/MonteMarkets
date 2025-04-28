import requests
import time
import sys
import threading
import concurrent.futures

def run_simulation(ticker):
    thread_id = threading.current_thread().name
    print(f"{thread_id}: Starting simulation for {ticker}")
    
    # Start simulation
    response = requests.get(f"http://172.25.32.1:8000/simulate/{ticker}?num_simulations=100")
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"{thread_id}: Job ID: {job_id}")
    
    # Poll for results
    while True:
        result_response = requests.get(f"http://172.25.32.1:8000/simulate/{ticker}/result/{job_id}")
        
        if result_response.status_code == 200:
            result = result_response.json()
            print(f"{thread_id}: Simulation complete for {ticker}!")
            print(f"{thread_id}: Expected final price: {result['expected_prices'][-1]}")
            break
        elif result_response.status_code == 202:
            status = result_response.json()
            print(f"{thread_id}: Status for {ticker}: {status.get('status', 'processing')}")
            time.sleep(2)
        else:
            print(f"{thread_id}: Error: {result_response.status_code}")
            print(result_response.text)
            break

# Run multiple simulations concurrently
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# Use ThreadPoolExecutor to run simulations concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=len(tickers)) as executor:
    # Submit all simulations to the executor
    futures = [executor.submit(run_simulation, ticker) for ticker in tickers]
    
    # Wait for all to complete (optional)
    concurrent.futures.wait(futures)

print("All simulations have been submitted and completed!")
