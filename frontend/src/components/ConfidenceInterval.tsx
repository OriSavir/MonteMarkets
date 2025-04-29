'use client';

import { useState, useEffect } from 'react';
import { calculateConfidenceInterval, formatCurrency } from '../lib/utils';

interface ConfidenceIntervalProps {
  finalPrices: number[];
  initialInterval: [number, number];
}

export default function ConfidenceInterval({ finalPrices, initialInterval }: ConfidenceIntervalProps) {
  const [confidenceLevel, setConfidenceLevel] = useState(0.95);
  const [interval, setInterval] = useState<[number, number]>(initialInterval);

  useEffect(() => {
    const newInterval = calculateConfidenceInterval(finalPrices, confidenceLevel);
    setInterval(newInterval);
  }, [confidenceLevel, finalPrices]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value) / 100;
    if (!isNaN(value) && value > 0 && value < 1) {
      setConfidenceLevel(value);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Closing Price Confidence Interval</h3>
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <p className="text-gray-700 mb-2">
            With {(confidenceLevel * 100).toFixed(0)}% confidence, the closing price will be between:
          </p>
          <p className="text-2xl font-bold text-blue-600">
            {formatCurrency(interval[0])} - {formatCurrency(interval[1])}
          </p>
        </div>
        <div className="w-full md:w-64">
          <label htmlFor="confidence" className="block text-sm font-medium text-gray-700 mb-1">
            Confidence Level: {(confidenceLevel * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            id="confidence"
            min="50"
            max="99"
            step="1"
            value={confidenceLevel * 100}
            onChange={handleChange}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}
