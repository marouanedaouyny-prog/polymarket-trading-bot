import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, postJson } from "../lib/api";
import { formatCurrency, shortTime } from "../lib/format";
import type { StatusResponse, TradesResponse } from "../lib/types";

export default function TradesPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [trades, setTrades] = useState<TradesResponse["trades"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, tradesRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<TradesResponse>("/api/trades?limit=200"),
      ]);
      setStatus(statusRes);
      setTrades(tradesRes.trades);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trades");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [autoRefresh, refresh]);

  const stats = useMemo(() => {
    const wins = trades.filter((trade) => trade.win).length;
    const volume = trades.reduce((sum, trade) => sum + trade.position_size, 0);
    const pnl = trades.reduce((sum, trade) => sum + trade.pnl, 0);
    return {
      count: trades.length,
      winRate: trades.length > 0 ? (wins / trades.length) * 100 : 0,
      volume,
      pnl,
    };
  }, [trades]);

  return (
    <>
      <Head>
        <title>Trades | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="trades"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void postJson("/api/stop").then(() => refresh()).catch(() => setError("Failed to trigger killswitch"));
        }}
      >
        {loading ? <LoadingPanel label="Loading trades" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}

        {!loading && !error ? (
          <>
            <section className="kpi-grid" style={{ marginBottom: 12 }}>
              <div className="kpi-card">
                <div className="kpi-label">24h Trades</div>
                <div className="kpi-value">{stats.count}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">24h Volume</div>
                <div className="kpi-value good">{formatCurrency(stats.volume)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Win Rate</div>
                <div className={`kpi-value ${stats.winRate >= 55 ? "good" : "warn"}`}>{stats.winRate.toFixed(2)}%</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Net PnL</div>
                <div className={`kpi-value ${stats.pnl >= 0 ? "good" : "bad"}`}>{formatCurrency(stats.pnl)}</div>
              </div>
            </section>

            <section className="card" style={{ marginBottom: 12 }}>
              <div className="inline-form" style={{ justifyContent: "space-between" }}>
                <div className="inline-form">
                  <button className="btn" type="button">Today</button>
                  <button className="btn" type="button">All Sides</button>
                  <button className="btn" type="button">Filled Only</button>
                </div>
                <label className="inline-form small muted" style={{ gap: 6 }}>
                  Auto-refresh
                  <input checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} type="checkbox" />
                </label>
              </div>
            </section>

            <section className="card">
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Market</th>
                      <th>Side</th>
                      <th style={{ textAlign: "right" }}>Entry Price</th>
                      <th style={{ textAlign: "right" }}>Size</th>
                      <th style={{ textAlign: "right" }}>PnL</th>
                      <th style={{ textAlign: "center" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade) => (
                      <tr key={trade.id}>
                        <td>{shortTime(trade.timestamp)}</td>
                        <td>{trade.question}</td>
                        <td>
                          <span className={`badge ${trade.side.toUpperCase() === "YES" ? "good" : "warn"}`}>{trade.side}</span>
                        </td>
                        <td style={{ textAlign: "right" }}>{trade.entry_price.toFixed(4)}</td>
                        <td style={{ textAlign: "right" }}>{formatCurrency(trade.position_size)}</td>
                        <td style={{ textAlign: "right" }} className={trade.pnl >= 0 ? "value-good" : "value-bad"}>
                          {formatCurrency(trade.pnl)}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <span className={`badge ${trade.win ? "good" : "bad"}`}>{trade.win ? "filled" : "loss"}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </TerminalShell>
    </>
  );
}

