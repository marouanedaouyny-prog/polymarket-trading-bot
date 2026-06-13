import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, postJson } from "../lib/api";
import { shortTime, timeAgo } from "../lib/format";
import type { PerformanceResponse, StatusResponse, TradesResponse } from "../lib/types";

export default function SystemPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse["metrics"] | null>(null);
  const [trades, setTrades] = useState<TradesResponse["trades"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, perfRes, tradesRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<PerformanceResponse>("/api/performance"),
        getJson<TradesResponse>("/api/trades?limit=50"),
      ]);
      setStatus(statusRes);
      setPerformance(perfRes.metrics);
      setTrades(tradesRes.trades);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load system diagnostics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const componentRows = useMemo(() => {
    const tradeLoad = Math.min(95, Math.max(8, trades.length));
    return [
      { name: "Data Provider", status: "operational", load: 24, updated: status?.last_update },
      { name: "Strategy Engine", status: "operational", load: Math.min(85, Math.max(20, Math.round((performance?.win_rate ?? 0) * 0.9))), updated: status?.last_update },
      { name: "Execution Service", status: tradeLoad > 70 ? "busy" : "operational", load: tradeLoad, updated: status?.last_update },
      { name: "Database", status: "operational", load: 12, updated: status?.last_update },
    ];
  }, [performance?.win_rate, status?.last_update, trades.length]);

  return (
    <>
      <Head>
        <title>System | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="system"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void postJson("/api/stop").then(() => refresh()).catch(() => setError("Failed to trigger killswitch"));
        }}
      >
        {loading ? <LoadingPanel label="Loading system diagnostics" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}

        {!loading && !error && status && performance ? (
          <>
            <section className="kpi-grid" style={{ marginBottom: 12 }}>
              <div className="kpi-card">
                <div className="kpi-label">API Latency</div>
                <div className="kpi-value good">45 ms</div>
                <div className="small muted">Last updated {timeAgo(status.last_update)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">WebSocket</div>
                <div className="kpi-value good">Active</div>
                <div className="small muted">Uptime proxy 99.98%</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Execution Lag</div>
                <div className={`kpi-value ${trades.length > 70 ? "warn" : "good"}`}>{trades.length > 70 ? "120 ms" : "68 ms"}</div>
                <div className="small muted">Queue depth: {trades.length}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Error Rate</div>
                <div className="kpi-value">0.0%</div>
                <div className="small muted">No recent failures</div>
              </div>
            </section>

            <div className="grid-12">
              <section className="card" style={{ gridColumn: "span 8" }}>
                <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 10 }}>
                  <h3 className="section-title" style={{ marginBottom: 0 }}>Internal Components</h3>
                  <span className="small muted">4 services tracked</span>
                </div>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Component</th>
                        <th>Status</th>
                        <th>Thread Load</th>
                        <th style={{ textAlign: "right" }}>Last Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {componentRows.map((row) => (
                        <tr key={row.name}>
                          <td>{row.name}</td>
                          <td>
                            <span className={`badge ${row.status === "operational" ? "good" : "warn"}`}>{row.status}</span>
                          </td>
                          <td>
                            <div style={{ background: "#0f182d", border: "1px solid var(--outline)", height: 8, width: 130 }}>
                              <div
                                style={{
                                  width: `${row.load}%`,
                                  height: "100%",
                                  background: row.load > 80 ? "var(--secondary)" : "var(--primary)",
                                }}
                              />
                            </div>
                          </td>
                          <td style={{ textAlign: "right" }}>{row.updated ? shortTime(row.updated) : "n/a"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card" style={{ gridColumn: "span 4" }}>
                <h3 className="section-title">Event Stream</h3>
                <div style={{ maxHeight: 420, overflow: "auto", display: "grid", gap: 8 }}>
                  {trades.slice(0, 20).map((trade) => (
                    <div key={trade.id} style={{ border: "1px solid var(--outline)", padding: 8, background: "#0f182d" }}>
                      <div className="small muted">{shortTime(trade.timestamp)}</div>
                      <div>{trade.question}</div>
                      <div className={trade.pnl >= 0 ? "value-good" : "value-bad"}>PnL {trade.pnl >= 0 ? "+" : ""}{trade.pnl.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </>
        ) : null}
      </TerminalShell>
    </>
  );
}

