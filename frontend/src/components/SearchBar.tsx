'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SearchBar() {
    const [ticker, setTicker] = useState('');
    const router = useRouter();

    const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (ticker.trim()) {
        router.push(`/${ticker.toUpperCase()}`);
    }
    };

    return (
    <form onSubmit={handleSubmit} className="w-full max-w-md mx-auto">
        <div className="relative flex items-center">
        <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="Enter stock ticker (e.g., AAPL)"
            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
            type="submit"
            className="absolute right-2 p-2 text-gray-600 hover:text-blue-500"
            aria-label="Search"
        >
            <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            >
            <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
            </svg>
        </button>
        </div>
    </form>
    );
}
