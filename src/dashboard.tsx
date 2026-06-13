import React, { useState, useEffect } from 'react';

// Mock data for demonstration
const mockMarkets = [
  { id: '1', name: 'Trump Wins 2024 Election', price: 0.65, volume: 1250000 },
  { id: '2', name: 'Bitcoin > $50K by Dec', price: 0.45, volume: 850000 },
  { id: '3', name: 'Fed Rate Cut in May', price: 0.30, volume: 450000 }
];

const mockPerformance = {
  today_pnl: 1250.75,
  total_pnl: 15420.50,
  open_positions: 3,
  win_rate: 0.65
};

export default function TradingDashboard() {
  const [markets, setMarkets] = useState(mockMarkets);
  const [systemStatus, setSystemStatus] = useState('operational');
  const [performance, setPerformance] = useState(mockPerformance);

  // In a real implementation, this would fetch live data
  useEffect(() => {
    // Simulate periodic data updates
    const interval = setInterval(() => {
      // Update mock data periodically
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-center">Polymarket Trading Dashboard</h1>
          <p className="text-gray-400 text-center">Real-time Market Monitoring</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {/* System Status Card */}
          <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
            <h2 className="text-xl font-bold mb-4">System Status</h2>
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
                <span>{performance.open_positions}</span>
              </div>
              <div className="flex justify-between">
                <span>Today's PnL:</span>
                <span className="text-green-400">+${performance.today_pnl.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Market Overview */}
          <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
            <h2 className="text-xl font-bold mb-4">Market Overview</h2>
            <div className="space-y-4">
              {markets.map((market) => (
                <div key={market.id} className="border-b border-gray-700 pb-2">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-medium">{market.name}</div>
                      <div className="text-sm text-gray-400">Volume: ${market.volume.toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-cyan-400 font-mono">{market.price.toFixed(4)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Management */}
          <div className="bg-gray-800 rounded-lg p-6 shadow-xl">
            <h2 className="text-xl font-bold mb-4">Risk Management</h2>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Max Drawdown:</span>
                <span className="text-red-400">0.00%</span>
              </div>
              <div className="flex justify-between">
                <span>Daily PnL:</span>
                <span className="text-green-400">+${performance.today_pnl.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Total PnL:</span>
                <span className="text-green-400">+${performance.total_pnl.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Win Rate:</span>
                <span>{(performance.win_rate * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}