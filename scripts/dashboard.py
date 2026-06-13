# Trading Dashboard Application
# Built with Next.js 15, TypeScript, and Tailwind CSS

import React, { useState, useEffect } from 'react';

const TradingDashboard = () => {
  const [markets, setMarkets] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [positions, setPositions] = useState([]);
  const [systemStatus, setSystemStatus] = useState('operational');

  useEffect(() => {
    // Simulate fetching data
    const fetchData = async () => {
      try {
        const response = await fetch('/api/markets');
        const data = await response.json();
        setMarkets(data.markets || []);
      } catch (error) {
        console.error('Failed to fetch market data:', error);
      }
    };

    // Fetch data initially
    fetchData();

    // Set up polling for real-time updates
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Polymarket AI Trading Dashboard</h1>
        <p className="text-gray-400">Real-time monitoring of trading activities</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* System Status Card */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">System Status</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span>Trading Status:</span>
              <span className="text-green-400 font-semibold">Operational</span>
            </div>
            <div className="flex justify-between">
              <span>Active Strategies:</span>
              <span>3</span>
            </div>
            <div className="flex justify-between">
              <span>Open Positions:</span>
              <span>{positions.length}</span>
            </div>
          </div>
        </div>

        {/* Market Overview Card */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Market Overview</h2>
          <div className="space-y-2">
            {markets.slice(0, 5).map((market, index) => (
              <div key={index} className="flex justify-between border-b border-gray-700 pb-2">
                <span>{market.symbol || 'Unknown'}</span>
                <span className="text-cyan-400">${market.price || 'N/A'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Trading Opportunities Card */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Arbitrage Opportunities</h2>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-4 text-sm font-medium">
              <span>Market</span>
              <span>Profit %</span>
              <span>Confidence</span>
            </div>
            {opportunities.map((opp, index) => (
              <div key={index} className="grid grid-cols-3 gap-4 text-sm">
                <span>{opp.symbol || 'Unknown'}</span>
                <span className={opp.expected_profit > 0 ? "text-green-400" : "text-red-400"}>
                  {opp.expected_profit ? `${(opp.expected_profit * 100).toFixed(2)}%` : 'N/A'}
                </span>
                <span>{(opp.confidence * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Management Card */}
        <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-xl font-semibold mb-4">Risk Management</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Max Drawdown:</span>
              <span className="text-red-400">0.00%</span>
            </div>
            <div className="flex justify-between">
              <span>Daily PnL:</span>
              <span className="text-green-400">+$0.00</span>
            </div>
            <div className="flex justify-between">
              <span>Active Positions:</span>
              <span>{positions.length}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingDashboard;