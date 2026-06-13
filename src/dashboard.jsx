import React from 'react';

const TradingDashboard = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black text-white p-4">
      {/* Header */}
      <header className="text-center mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
          Polymarket AI Trading Dashboard
        </h1>
        <p className="text-gray-400">Real-time Prediction Market Trading Interface</p>
      </header>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* System Status */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 shadow-lg">
          <h2 className="text-xl font-bold mb-4 text-cyan-400">System Status</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span>Trading Status:</span>
              <span className="text-green-400 font-semibold">Operational</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Active Strategies:</span>
              <span>3</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Open Positions:</span>
              <span>0</span>
            </div>
            <div className="flex justify-between items-center">
              <span>System Uptime:</span>
              <span className="text-green-400">100%</span>
            </div>
          </div>
        </div>

        {/* Market Overview */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 shadow-lg">
          <h2 className="text-xl font-bold mb-4 text-cyan-400">Market Overview</h2>
          <div className="space-y-4">
            <div className="border-b border-gray-700 pb-3">
              <h3 className="font-semibold text-cyan-400">Top Markets</h3>
              <ul className="list-disc pl-5 mt-2 space-y-2 text-sm">
                <li className="flex justify-between">
                  <span>Market 1</span>
                  <span className="text-green-400">58%</span>
                </li>
                <li className="flex justify-between">
                  <span>Market 2</span>
                  <span className="text-green-400">42%</span>
                </li>
                <li className="flex justify-between">
                  <span>Market 3</span>
                  <span className="text-green-400">35%</span>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-cyan-400">24h Trading Activity</h3>
              <p className="mt-2">Volume: <span className="text-green-400">$1.2M</span></p>
            </div>
          </div>
        </div>

        {/* Risk Management */}
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 shadow-lg">
          <h2 className="text-xl font-bold mb-4 text-cyan-400">Risk Management</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Max Drawdown:</span>
              <span className="text-red-400">0.00%</span>
            </div>
            <div className="flex justify-between">
              <span>System Status:</span>
              <span className="text-green-400">+$0.00</span>
            </div>
            <div className="flex justify-between">
              <span>Active Positions:</span>
              <span>0</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 shadow-lg">
          <div className="mb-4">
            <h2 className="text-xl font-bold mb-4 text-cyan-400">Trading Controls</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold text-cyan-400">Auto-trading</h3>
                <p className="text-green-400">ON</p>
              </div>
              <div>
                <h3 className="font-semibold text-cyan-400">Risk Controls</h3>
                <p className="text-green-400">ON</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6 border border-gray-700 shadow-lg">
          <h2 className="text-xl font-bold mb-4 text-cyan-400">System Health</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>CPU:</span>
              <span className="text-cyan-400">5%</span>
            </div>
            <div className="flex justify-between">
              <span>Memory:</span>
              <span className="text-cyan-400">45%</span>
            </div>
            <div className="flex justify-between">
              <span>Network:</span>
              <span className="text-green-400">100%</span>
            </div>
            <div className="flex justify-between">
              <span>Database:</span>
              <span className="text-green-400">Connected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradingDashboard;