from fastapi import FastAPI
from .utils import generate_simulation_data
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from datetime import date
from typing import Dict, Tuple, List

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "This is the root endpoint for the FastAPI application"}


class SimulationResponse(BaseModel):
    prices: List[List[float]]
    expected_prices: List[float]
    intervals: Dict[float, Tuple[float, float]]
    recent_open_date: date


@app.get("/simulate/{ticker}")
async def simulate(ticker: str):
    """
    The endpoint to run a Monte Carlo simulation on a given ticker.
    """
    try:
        ticker = ticker.upper()
        if not ticker.isalpha():
            raise ValueError("Ticker must be alphabetic characters only")
        if len(ticker) < 1 or len(ticker) > 5:
            raise ValueError("Ticker length must be between 1 and 5 characters")
        simulation_data, expected_p_data, confidence_intervals, recent_open_date = generate_simulation_data(ticker)
        response = SimulationResponse(
            prices=simulation_data.tolist(),
            expected_prices=expected_p_data.tolist(),
            intervals=confidence_intervals,
            recent_open_date=recent_open_date
        )
        return JSONResponse(content=jsonable_encoder(response), status_code=200)
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": "An unexpected error occurred: " + str(e)}, status_code=500)
    
    