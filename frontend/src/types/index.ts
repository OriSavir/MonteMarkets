export interface SimulationResponse {
    prices: number[][];
    expected_prices: number[];
    intervals: [number, number];
    recent_open_date: string;
    final_prices: number[];
}
  
export interface SimulationJobResponse {
    job_id: string;
}
  
export interface SimulationStatusResponse {
    status: "queued" | "in_progress";
}
  