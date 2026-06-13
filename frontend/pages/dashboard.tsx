import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, getWebSocketUrl, postJson } from "../lib/api";
import { formatCurrency, formatPercent, shortTime, timeAgo } from "../lib/format";
import type { PerformanceResponse, StatusResponse, TradesResponse } from "../lib/types";

export default function DashboardPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse["metrics"] | null>(null);
  const [trades, setTrades] = useState<TradesResponse["trades"]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastWsEvent, setLastWsEvent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, perfRes, tradesRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<PerformanceResponse>("/api/performance"),
        getJson<TradesResponse>("/api/trades?limit=10"),
      ]);
      setStatus(statusRes);
      setPerformance(perfRes.metrics);
      setTrades(tradesRes.trades);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => {
      void refresh();
    }, 5000);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    const ws = new WebSocket(getWebSocketUrl());

    ws.onopen = () => {
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      setLastWsEvent(new Date().toISOString());
      try {
        const msg = JSON.parse(event.data) as {
          type?: string;
          data?: {
            balance?: number;
            total_trades?: number;
            win_rate?: number;
            timestamp?: string;
          };
        };
        if (msg.type === "state" && msg.data) {
          setStatus((previous) => {
            if (!previous) {
              return previous;
            }
            return {
              ...previous,
              balance: Number(msg.data.balance ?? previous.balance),
              total_trades: Number(msg.data.total_trades ?? previous.total_trades),
              win_rate: Number(msg.data.win_rate ?? previous.win_rate),
              last_update: msg.data.timestamp ?? previous.last_update,
            };
          });
        }
      } catch {
        // Ignore malformed payloads from stale clients.
      }
    };

    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    return () => ws.close();
  }, []);

  const handleStart = useCallback(async () => {
    await postJson("/api/start");
    await refresh();
  }, [refresh]);

  const handlePause = useCallback(async () => {
    await postJson("/api/pause");
    await refresh();
  }, [refresh]);

  const handleStop = useCallback(async () => {
    await postJson("/api/stop");
    await refresh();
  }, [refresh]);

  const controlDisabled = !status;

  const winRateBand = useMemo(() => {
    if (!status) return "neutral";
    if (status.win_rate >= 70) return "good";
    if (status.win_rate >= 50) return "warn";
    return "bad";
  }, [status]);

  return (
    <>
      <Head>
        <title>Overview | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="overview"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void handleStop();
        }}
        topRight={<span className="small muted">WS: {wsConnected ? "online" : "offline"}</span>}
      >
        {loading ? <LoadingPanel label="Loading overview" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}

        {!loading && !error && status && performance ? (
          <div className="grid-12">
            <section className="card" style={{ gridColumn: "span 8" }}>
              <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 14 }}>
                <div>
                  <h3 className="section-title">Dashboard Overview</h3>
                  <p className="small muted">Real-time performance telemetry for BOT-01 execution cluster.</p>
                </div>
                <div className="inline-form">
                  <button className="btn btn-primary" disabled={controlDisabled} onClick={() => void handleStart()} type="button">
                    Start
                  </button>
                  <button className="btn btn-secondary" disabled={controlDisabled} onClick={() => void handlePause()} type="button">
                    Pause
                  </button>
                  <button className="btn btn-danger" disabled={controlDisabled} onClick={() => void handleStop()} type="button">
                    Stop
                  </button>
                </div>
              </div>

              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-label">Current Balance</div>
                  <div className="kpi-value">{formatCurrency(status.balance)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Realized PnL</div>
                  <div className={`kpi-value ${status.profit >= 0 ? "good" : "bad"}`}>{formatCurrency(status.profit)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">ROI (Cumulative)</div>
                  <div className={`kpi-value ${status.roi >= 0 ? "good" : "bad"}`}>{formatPercent(status.roi)}</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Max Drawdown</div>
                  <div className="kpi-value warn">{formatPercent(-Math.abs(performance.max_drawdown), 2)}</div>
                </div>
              </div>
            </section>

            <section className="card" style={{ gridColumn: "span 4" }}>
              <h3 className="section-title">Stream Health</h3>
              <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <span className="muted">WebSocket</span>
                <span className={`badge ${wsConnected ? "good" : "warn"}`}>{wsConnected ? "stable" : "reconnecting"}</span>
              </div>
              <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <span className="muted">Last update</span>
                <span>{timeAgo(status.last_update)}</span>
              </div>
              <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <span className="muted">Win rate state</span>
                <span className={`value-${winRateBand}`}>{formatPercent(status.win_rate)}</span>
              </div>
              <div className="inline-form" style={{ justifyContent: "space-between" }}>
                <span className="muted">Last WS event</span>
                <span>{lastWsEvent ? timeAgo(lastWsEvent) : "none"}</span>
              </div>
            </section>

            <section className="card" style={{ gridColumn: "span 4" }}>
              <h3 className="section-title">Execution Summary</h3>
              <div className="kpi-card" style={{ marginBottom: 10 }}>
                <div className="kpi-label">Win Rate</div>
                <div className={`kpi-value ${winRateBand === "good" ? "good" : winRateBand === "warn" ? "warn" : "bad"}`}>
                  {formatPercent(status.win_rate)}
                </div>
              </div>
              <div className="kpi-card" style={{ marginBottom: 10 }}>
                <div className="kpi-label">Total Trades</div>
                <div className="kpi-value">{performance.total_trades}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Sharpe (proxy)</div>
                <div className="kpi-value good">{performance.sharpe_ratio.toFixed(2)}</div>
              </div>
            </section>

            <section className="card" style={{ gridColumn: "span 8" }}>
              <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                <h3 className="section-title" style={{ marginBottom: 0 }}>Live Executions</h3>
                <span className="small muted">Total Trades: {status.total_trades}</span>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Market</th>
                      <th>Side</th>
                      <th>Size</th>
                      <th>Price</th>
                      <th>PnL</th>
                      <th style={{ textAlign: "right" }}>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade) => (
                      <tr key={trade.id}>
                        <td>{trade.question}</td>
                        <td>
                          <span className={`badge ${trade.side.toUpperCase() === "YES" ? "good" : "warn"}`}>{trade.side}</span>
                        </td>
                        <td>{formatCurrency(trade.position_size)}</td>
                        <td>{trade.entry_price.toFixed(2)}</td>
                        <td className={trade.pnl >= 0 ? "value-good" : "value-bad"}>{formatCurrency(trade.pnl)}</td>
                        <td style={{ textAlign: "right" }} className="muted">{shortTime(trade.timestamp)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        ) : null}
      </TerminalShell>
    </>
  );
}

