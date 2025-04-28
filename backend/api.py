from fastapi import FastAPI
from .utils import generate_simulation_data, clean_numpy
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import numpy as np

from redis import Redis
from rq import Queue
import uuid

from datetime import date
from typing import Dict, Tuple, List, Optional

from dotenv import load_dotenv
import os

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))


app = FastAPI()

@app.get("/")
async def root():
    return {"message": "This is the root endpoint for the FastAPI application"}


class SimulationRequest(BaseModel):
    ticker: str
    num_simulations: int = 1000
    random_seed: int = None

class SimulationResponse(BaseModel):
    prices: List[List[float]]
    expected_prices: List[float]
    intervals: Tuple[float, float]
    recent_open_date: date
    final_prices: List[float]

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
q = Queue(connection=redis_conn)

@app.get("/simulate/{ticker}")
async def simulate(ticker: str, num_simulations: int= 1000, random_seed: Optional[int] = None):
    """
    The endpoint to run a Monte Carlo simulation on a given ticker.
    """
    job_id = str(uuid.uuid4())
    job = q.enqueue(
        generate_simulation_data, 
        ticker, 
        num_simulations, 
        random_seed, 
        job_id=job_id,
        job_timeout=300,
        result_ttl=300,
    )
    return JSONResponse(content={"job_id": job_id}, status_code=202)


@app.get("/simulate/{ticker}/result/{job_id}", response_model=SimulationResponse)
async def get_simulation_result(ticker: str, job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.is_finished:
        result = job.result

        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="Invalid job result format")
        return SimulationResponse(**result)

    elif job.is_failed:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.exc_info}")

    elif job.is_queued:
        return JSONResponse(content={"status": "queued"}, status_code=202)

    elif job.is_started:
        return JSONResponse(content={"status": "in_progress"}, status_code=202)


