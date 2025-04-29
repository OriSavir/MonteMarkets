'use client';

import { useEffect, useRef } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { generateTimeLabels } from '../lib/utils';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
);

interface SimulationChartProps {
    prices: number[][];
    expectedPrices: number[];
    date: string;
}

export default function SimulationChart({ prices, expectedPrices, date }: SimulationChartProps) {
    const chartRef = useRef<ChartJS<"line">>(null);
    const timeLabels = generateTimeLabels();

    // Create datasets for all simulation lines

    const sampleSimulations = (simulations: number[][], sampleSize: number = 100) => {
        if (simulations.length <= sampleSize) return simulations;
        
        const result = [];
        const step = Math.floor(simulations.length / sampleSize);
        
        for (let i = 0; i < simulations.length; i += step) {
            if (result.length < sampleSize) {
                result.push(simulations[i]);
            }
        }
        
        return result;
    };

    const simulationDatasets = sampleSimulations(prices, 100).map((simulation, index) => ({
        data: simulation,
        borderColor: 'rgba(156, 163, 175, 0.1)',
        backgroundColor: 'rgba(156, 163, 175, 0)',
        pointRadius: 0,
        borderWidth: 1,
        // Make simulation lines not interactive with tooltips
        tooltip: {
            enabled: false
        },
        // Don't include these in the legend
        showLine: true,
    }));

    // Create dataset for expected prices (with high opacity)
    const expectedDataset = {
        label: 'Expected Price',
        data: expectedPrices,
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        borderWidth: 2,
        pointRadius: 0,
        // Make this the only line that shows in tooltips
        tooltip: {
            enabled: true
        },
    };

    const data = {
        labels: timeLabels,
        datasets: [
            ...simulationDatasets,
            expectedDataset,
        ],
    };

    const options: ChartOptions<'line'> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: `${date} Monte Carlo Price Estimation`,
                font: {
                    size: 16,
                    weight: 'bold',
                },
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                filter: (tooltipItem) => {
                    // Only show tooltip for the expected price dataset (last dataset)
                    return tooltipItem.datasetIndex === simulationDatasets.length;
                },
                callbacks: {
                    title: (tooltipItems) => {
                        return `Time: ${tooltipItems[0].label}`;
                    },
                    label: (context) => {
                        return `Expected Price: $${context.parsed.y.toFixed(2)}`;
                    }
                }
            },
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Time (EST)',
                },
                ticks: {
                    maxRotation: 45,
                    minRotation: 45,
                },
            },
            y: {
                title: {
                    display: true,
                    text: 'Price ($)',
                },
                ticks: {
                    callback: (value) => {
                        return `$${value}`;
                    }
                }
            },
        },
    };

    return (
        <div className="w-full h-96 bg-white p-4 rounded-lg shadow-md">
            <Line ref={chartRef} options={options} data={data} />
        </div>
    );
}
