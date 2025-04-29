'use client';

import { useState, useEffect } from 'react';
import { calculateProbability, formatPercentage } from '../lib/utils';

interface ProbabilityCalculatorProps {
  prices: number[][];
  currentPrice: number;
}

export default function ProbabilityCalculator({ prices, currentPrice }: ProbabilityCalculatorProps) {
  const [targetPrice, setTargetPrice] = useState<string>('');
  const [probability, setProbability] = useState<number | null>(null);

  useEffect(() => {
    const calculateProb = () => {
      const target = parseFloat(targetPrice);
      if (!isNaN(target) && target > 0) {
        const prob = calculateProbability(prices, target);
        setProbability(prob);
      } else {
        setProbability(null);
      }
    };

    const debounce = setTimeout(calculateProb, 500);
    return () => clearTimeout(debounce);
  }, [targetPrice, prices]);

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Price Target Probability</h3>
      <div className="flex flex-col md:flex-row md:items-end gap-4">
        <div className="flex-1">
          <label htmlFor="targetPrice" className="block text-sm font-medium text-gray-700 mb-1">
            Enter a price target
          </label>
          <input
            type="number"
            id="targetPrice"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            placeholder={`Current: ${currentPrice.toFixed(2)}`}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex-1">
          {probability !== null && (
            <div>
              <p className="text-gray-700 mb-1">Probability of reaching this price:</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatPercentage(probability)}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
