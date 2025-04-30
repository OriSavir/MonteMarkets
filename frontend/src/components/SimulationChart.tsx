'use client';

import { useRef, useMemo } from 'react';
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

export default function SimulationChart({
prices,
expectedPrices,
date,
}: SimulationChartProps) {
    const chartRef = useRef(null);
    const timeLabels = useMemo(() => generateTimeLabels(), []);
    console.log('expectedPrices', expectedPrices);
    console.log('price walk 1 ', prices[0]);
    console.log('price walk 2 ', prices[1]);

    const sampledPaths = useMemo(() => {
        if (prices.length <= 100) return prices;

        const indices = Array.from({ length: prices.length }, (_, i) => i);
        for (let i = indices.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [indices[i], indices[j]] = [indices[j], indices[i]];
        }

        return indices.slice(0, 100).map(idx => prices[idx]);
    }, [prices]);

    const data = {
    labels: timeLabels,
    datasets: [
        ...sampledPaths.map((path) => ({
        label: 'Simulation',
        data: path,
        borderColor: 'rgba(102,211,115,0.17)',
        borderWidth: 1,
        pointRadius: 0,
        pointHoverRadius: 0,
        tension: 0,
        fill: false,
        })),
        {
        label: 'Expected Price',
        data: expectedPrices,
        borderColor: 'rgba(59,130,246,1)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        hoverBorderWidth: 3,
        tension: 0.2,
        fill: false,
        },
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
        font: { size: 16, weight: 'bold' },
        },
        tooltip: {
        mode: 'index',
        intersect: false,
        filter: (tooltipItem) => tooltipItem.dataset.label === 'Expected Price',
        callbacks: {
            title: (items) => `Time: ${items[0].label}`,
            label: (ctx) =>
            `Expected Price: $${(ctx.parsed.y as number).toFixed(2)}`,
        },
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
            text: 'Time (EST)' 
        },
        ticks: {
            callback: function (val, idx) {
            const label = this.getLabelForValue(val as number);
            if (!label) return '';
            
            const [h, m] = label.split(':').map(Number);
            return m % 15 === 0 ? label : '';
            },
            maxRotation: 45,
            minRotation: 45,
        },
        grid: {
            color: (ctx) => {
            if (!ctx.tick || ctx.index === undefined) return 'rgba(0,0,0,0.05)';
            
            const label = timeLabels[ctx.index];
            if (!label) return 'rgba(0,0,0,0.05)';
            
            return label.endsWith(':00')
                ? 'rgba(0,0,0,0.1)'
                : 'rgba(0,0,0,0.05)';
            },
        },
        },
        y: {
        title: { 
            display: true, 
            text: 'Price ($)' 
        },
        ticks: {
            callback: (v) => `$${v}`,
        },
        },
    },
    };

    return (
    <div className="w-full h-96 bg-white p-4 rounded-lg shadow-md">
        <Line ref={chartRef} data={data} options={options} />
    </div>
    );
}
