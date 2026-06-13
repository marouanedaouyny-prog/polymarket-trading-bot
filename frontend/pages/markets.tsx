import Head from "next/head";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, postJson } from "../lib/api";
import { formatCurrency } from "../lib/format";
import type { Market, MarketsResponse, StatusResponse } from "../lib/types";

export default function MarketsPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("All");
  const [minEdge, setMinEdge] = useState(0);
  const [minLiquidity, setMinLiquidity] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, marketsRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<MarketsResponse>("/api/markets?limit=100"),
      ]);
      setStatus(statusRes);
      setMarkets(marketsRes.markets);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load markets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 6000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const categories = useMemo(() => {
    const values = Array.from(new Set(markets.map((m) => m.category))).sort();
    return ["All", ...values];
  }, [markets]);

  const filtered = useMemo(() => {
    return markets
      .filter((m) => (category === "All" ? true : m.category === category))
      .filter((m) => m.edge * 100 >= minEdge)
      .filter((m) => m.liquidity >= minLiquidity)
      .sort((a, b) => b.edge - a.edge);
  }, [markets, category, minEdge, minLiquidity]);

  const onTrade = useCallback(async (marketId: string) => {
    try {
      await postJson(`/api/trade/execute?market_id=${encodeURIComponent(marketId)}&position_size_pct=0.2`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trade request failed");
    }
  }, [refresh]);

  return (
    <>
      <Head>
        <title>Markets | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="markets"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void postJson("/api/stop").then(() => refresh()).catch(() => setError("Failed to trigger killswitch"));
        }}
      >
        {loading ? <LoadingPanel label="Loading markets" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}

        {!loading && !error ? (
          <div className="card" style={{ marginBottom: 12 }}>
            <div className="kpi-grid">
              <div>
                <label className="kpi-label">Category</label>
                <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="kpi-label">Min Edge (%)</label>
                <input
                  className="input"
                  type="number"
                  min={0}
                  step={0.1}
                  value={minEdge}
                  onChange={(e) => setMinEdge(Number(e.target.value) || 0)}
                />
              </div>
              <div>
                <label className="kpi-label">Liquidity Floor</label>
                <input
                  className="input"
                  type="number"
                  min={0}
                  step={1000}
                  value={minLiquidity}
                  onChange={(e) => setMinLiquidity(Number(e.target.value) || 0)}
                />
              </div>
              <div style={{ display: "flex", alignItems: "end" }}>
                <button className="btn btn-primary" style={{ width: "100%" }} onClick={() => void refresh()} type="button">
                  Refresh Analysis
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {!loading && !error ? (
          <section className="card">
            <div className="inline-form" style={{ justifyContent: "space-between", marginBottom: 10 }}>
              <h3 className="section-title" style={{ marginBottom: 0 }}>Market Analysis</h3>
              <span className="small muted">Showing {filtered.length} / {markets.length}</span>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Market Question</th>
                    <th style={{ textAlign: "right" }}>Category</th>
                    <th style={{ textAlign: "right" }}>Yes / No</th>
                    <th style={{ textAlign: "right" }}>Volume</th>
                    <th style={{ textAlign: "right" }}>Liquidity</th>
                    <th style={{ textAlign: "right" }}>Edge</th>
                    <th style={{ textAlign: "right" }}>Confidence</th>
                    <th style={{ textAlign: "center" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((market) => {
                    const confidenceBand = market.confidence >= 75 ? "good" : market.confidence >= 55 ? "warn" : "bad";
                    return (
                      <tr key={market.id}>
                        <td>{market.question}</td>
                        <td style={{ textAlign: "right" }}>
                          <span className="badge">{market.category}</span>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <span className="value-good">{(market.yes_price * 100).toFixed(1)}¢</span>
                          <span className="muted"> / </span>
                          <span className="value-bad">{(market.no_price * 100).toFixed(1)}¢</span>
                        </td>
                        <td style={{ textAlign: "right" }}>{formatCurrency(market.volume)}</td>
                        <td style={{ textAlign: "right" }}>{formatCurrency(market.liquidity)}</td>
                        <td style={{ textAlign: "right" }} className={market.edge >= 0.4 ? "value-good" : "value-warn"}>
                          +{(market.edge * 100).toFixed(2)}%
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <span className={`badge ${confidenceBand}`}>{market.confidence}%</span>
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <button className="btn btn-primary" onClick={() => void onTrade(market.id)} type="button">
                            Trade
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </TerminalShell>
    </>
  );
}

