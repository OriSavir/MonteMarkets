import SearchBar from '../components/SearchBar';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-gray-50">
      <div className="w-full max-w-4xl mx-auto text-center">
        <h1 className="text-4xl font-bold mb-6 text-gray-900">
          Stock Price Monte Carlo Simulation
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Enter a stock ticker to run a Monte Carlo simulation and predict potential price movements.
        </p>
        <SearchBar />
      </div>
    </main>
  );
}
