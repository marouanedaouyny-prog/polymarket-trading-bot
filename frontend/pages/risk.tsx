import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, postJson } from "../lib/api";
import { formatCurrency, formatPercent, shortTime } from "../lib/format";
import type { MarketsResponse, PerformanceResponse, StatusResponse, TradesResponse } from "../lib/types";

export default function RiskPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse["metrics"] | null>(null);
  const [markets, setMarkets] = useState<MarketsResponse["markets"]>([]);
  const [trades, setTrades] = useState<TradesResponse["trades"]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, perfRes, marketsRes, tradesRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<PerformanceResponse>("/api/performance"),
        getJson<MarketsResponse>("/api/markets?limit=100"),
        getJson<TradesResponse>("/api/trades?limit=50"),
      ]);
      setStatus(statusRes);
      setPerformance(perfRes.metrics);
      setMarkets(marketsRes.markets);
      setTrades(tradesRes.trades);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load risk data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const exposures = useMemo(() => {
    const totals = new Map<string, number>();
    for (const market of markets) {
      totals.set(market.category, (totals.get(market.category) ?? 0) + market.volume);
    }

    const totalVolume = Array.from(totals.values()).reduce((sum, value) => sum + value, 0);
    return Array.from(totals.entries())
      .map(([category, volume]) => ({
        category,
        volume,
        percent: totalVolume > 0 ? (volume / totalVolume) * 100 : 0,
      }))
      .sort((a, b) => b.percent - a.percent);
  }, [markets]);

  const topExposure = exposures[0];

  const alerts = useMemo(() => {
    const maxDrawdown = performance?.max_drawdown ?? 0;
    return {
      critical: maxDrawdown > 12,
      warning: (topExposure?.percent ?? 0) > 40,
    };
  }, [performance, topExposure]);

  return (
    <>
      <Head>
        <title>Risk | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="risk"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void postJson("/api/stop").then(() => refresh()).catch(() => setError("Failed to trigger killswitch"));
        }}
      >
        {loading ? <LoadingPanel label="Loading risk" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}

        {!loading && !error && performance ? (
          <>
            <section className="alert-row" style={{ marginBottom: 12 }}>
              <div className="alert-card alert-critical">
                <div className="kpi-label">Critical</div>
                <div>{alerts.critical ? "Drawdown breach detected" : "No drawdown breach"}</div>
                <div className="small muted">Current drawdown: {formatPercent(-Math.abs(performance.max_drawdown), 2)}</div>
              </div>
              <div className="alert-card alert-warning">
                <div className="kpi-label">Warning</div>
                <div>{alerts.warning ? "Concentration warning" : "Concentration normal"}</div>
                <div className="small muted">
                  Top bucket: {topExposure ? `${topExposure.category} (${topExposure.percent.toFixed(1)}%)` : "n/a"}
                </div>
              </div>
              <div className="alert-card alert-info">
                <div className="kpi-label">Info</div>
                <div>Hedge scan required</div>
                <div className="small muted">Review pair exposure and position limits</div>
              </div>
            </section>

            <div className="grid-12">
              <section className="card" style={{ gridColumn: "span 8" }}>
                <h3 className="section-title">Category Exposure</h3>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th style={{ textAlign: "right" }}>Volume</th>
                        <th style={{ textAlign: "right" }}>Exposure</th>
                        <th>Gauge</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exposures.map((item) => (
                        <tr key={item.category}>
                          <td>{item.category}</td>
                          <td style={{ textAlign: "right" }}>{formatCurrency(item.volume)}</td>
                          <td style={{ textAlign: "right" }} className={item.percent > 40 ? "value-warn" : "value-good"}>
                            {item.percent.toFixed(2)}%
                          </td>
                          <td>
                            <div style={{ background: "#0f182d", border: "1px solid var(--outline)", height: 8 }}>
                              <div
                                style={{
                                  width: `${Math.min(item.percent, 100)}%`,
                                  height: "100%",
                                  background: item.percent > 40 ? "var(--secondary)" : "var(--primary)",
                                }}
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card" style={{ gridColumn: "span 4" }}>
                <h3 className="section-title">Killswitch Matrix</h3>
                <div className="kpi-card" style={{ marginBottom: 12 }}>
                  <div className="kpi-label">System State</div>
                  <div className={`kpi-value ${status?.bot_running ? "good" : "warn"}`}>
                    {status?.bot_running ? "inactive" : "active"}
                  </div>
                  <div className="small muted">Auto execution {status?.bot_running ? "enabled" : "disabled"}</div>
                </div>
                <button className="btn btn-danger" onClick={() => void postJson("/api/stop").then(() => refresh())} type="button">
                  Trigger Killswitch
                </button>
              </section>

              <section className="card" style={{ gridColumn: "span 6" }}>
                <h3 className="section-title">Position Sizing Policy</h3>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Variable</th>
                        <th>Value</th>
                        <th>Constraint</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Base Unit Size</td>
                        <td>0.25%</td>
                        <td>Equity Adjusted</td>
                      </tr>
                      <tr>
                        <td>Max Pair Cluster</td>
                        <td>4.00%</td>
                        <td>Category-Capped</td>
                      </tr>
                      <tr>
                        <td>Max Drawdown</td>
                        <td>{formatPercent(-Math.abs(performance.max_drawdown), 2)}</td>
                        <td>Hard Stop at -12%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card" style={{ gridColumn: "span 6" }}>
                <h3 className="section-title">Risk Event Feed</h3>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Market</th>
                        <th style={{ textAlign: "right" }}>PnL</th>
                        <th style={{ textAlign: "center" }}>Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.slice(0, 12).map((trade) => (
                        <tr key={trade.id}>
                          <td>{shortTime(trade.timestamp)}</td>
                          <td>{trade.question}</td>
                          <td style={{ textAlign: "right" }} className={trade.pnl < 0 ? "value-bad" : "value-good"}>
                            {formatCurrency(trade.pnl)}
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <span className={`badge ${trade.pnl < 0 ? "warn" : "good"}`}>{trade.pnl < 0 ? "warn" : "info"}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          </>
        ) : null}
      </TerminalShell>
    </>
  );
}

