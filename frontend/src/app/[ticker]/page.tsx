'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { startSimulation, getSimulationResult } from '../../lib/api';
import { SimulationResponse } from '../../types';
import { formatDateString } from '../../lib/utils';
import LoadingSpinner from '../../components/LoadingSpinner';
import SimulationChart from '../../components/SimulationChart';
import ConfidenceInterval from '../../components/ConfidenceInterval';
import ProbabilityCalculator from '../../components/ProbabilityCalculator';
import Link from 'next/link';

export default function TickerPage() {
  const { ticker } = useParams() as { ticker: string };
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function initiateSimulation() {
      try {
        setLoading(true);
        setError(null);
        const id = await startSimulation(ticker);
        setJobId(id);
      } catch (err) {
        setError(`Failed to start simulation: ${err instanceof Error ? err.message : String(err)}`);
        setLoading(false);
      }
    }

    initiateSimulation();
  }, [ticker]);

  useEffect(() => {
    if (!jobId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await getSimulationResult(ticker, jobId);
        
        if ('status' in response) {
          return;
        }
        
        setResult(response);
        setLoading(false);
        clearInterval(pollInterval);
      } catch (err) {
        setError(`Error fetching results: ${err instanceof Error ? err.message : String(err)}`);
        setLoading(false);
        clearInterval(pollInterval);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [jobId, ticker]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
          <Link href="/" className="text-blue-500 hover:underline">
            ← Back to search
          </Link>
        </div>
      </div>
    );
  }

  if (loading || !result) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-6 text-gray-900">
            Running simulation for {ticker}...
          </h1>
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  // Format the date from the API
  const date = formatDateString(result.recent_open_date);

  const currentTime = new Date();
  const marketOpenTime = new Date(currentTime);
  marketOpenTime.setHours(9, 30, 0, 0);
  let minutesSinceMarketOpen = Math.floor((currentTime.getTime() - marketOpenTime.getTime()) / (1000 * 60));
  minutesSinceMarketOpen = minutesSinceMarketOpen % 390;
  const currentPrice = result.expected_prices[Math.min(389, minutesSinceMarketOpen - 1)];
  //console.log('expected_prices', result.expected_prices);
  //console.log('first price walk ', result.prices[0]);
  //console.log('second price walk ', result.prices[1]);
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            {ticker} Simulation Results
          </h1>
          <Link href="/" className="text-blue-500 hover:underline">
            ← New Search
          </Link>
        </div>

        <div className="space-y-6">
          <SimulationChart 
            prices={result.prices} 
            expectedPrices={result.expected_prices} 
            date={date} 
          />
          
          <ConfidenceInterval 
            finalPrices={result.final_prices} 
            initialInterval={result.intervals} 
          />
          
          <ProbabilityCalculator 
            prices={result.prices} 
            currentPrice={currentPrice} 
          />
        </div>
      </div>
    </div>
  );
}
