import Head from "next/head";
import { useCallback, useEffect, useState } from "react";

import { TerminalShell } from "../components/terminal-shell";
import { ErrorPanel, LoadingPanel } from "../components/state-panels";
import { getJson, postJson } from "../lib/api";
import { formatCurrency } from "../lib/format";
import type { PerformanceResponse, StatusResponse } from "../lib/types";

export default function SettingsPage() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse["metrics"] | null>(null);
  const [startingBalance, setStartingBalance] = useState("10000");
  const [confirmReset, setConfirmReset] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusRes, perfRes] = await Promise.all([
        getJson<StatusResponse>("/api/status"),
        getJson<PerformanceResponse>("/api/performance"),
      ]);
      setStatus(statusRes);
      setPerformance(perfRes.metrics);
      setStartingBalance(String(perfRes.metrics.starting_balance));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveSettings = useCallback(async () => {
    try {
      const amount = Number(startingBalance);
      if (!Number.isFinite(amount) || amount <= 0) {
        setError("Starting balance must be a positive number");
        return;
      }
      await postJson(`/api/config?starting_balance=${encodeURIComponent(amount)}`);
      setMessage("Configuration updated.");
      setError(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update configuration");
    }
  }, [refresh, startingBalance]);

  const resetAccount = useCallback(async () => {
    try {
      await postJson("/api/reset");
      setMessage("Account reset complete.");
      setError(null);
      setConfirmReset(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset account");
    }
  }, [refresh]);

  return (
    <>
      <Head>
        <title>Settings | Polymarket Technical Console</title>
      </Head>
      <TerminalShell
        active="settings"
        title="Terminal Console"
        statusRunning={Boolean(status?.bot_running)}
        balance={status?.balance}
        onKillSwitch={() => {
          void postJson("/api/stop").then(() => refresh()).catch(() => setError("Failed to trigger killswitch"));
        }}
      >
        {loading ? <LoadingPanel label="Loading settings" /> : null}
        {error ? <ErrorPanel message={error} onRetry={() => void refresh()} /> : null}
        {message ? <div className="card alert-info">{message}</div> : null}

        {!loading && !error && status && performance ? (
          <div className="grid-12">
            <section className="card" style={{ gridColumn: "span 8" }}>
              <h3 className="section-title">Global Parameters</h3>
              <div className="kpi-card" style={{ marginBottom: 12 }}>
                <div className="kpi-label">Environment Mode</div>
                <div className="inline-form" style={{ marginTop: 6 }}>
                  <button className="btn btn-primary" type="button">Paper</button>
                  <button className="btn" type="button" disabled>Live Production</button>
                </div>
                <p className="small muted">Live mode is intentionally disabled in this environment.</p>
              </div>

              <div className="kpi-card" style={{ marginBottom: 12 }}>
                <div className="kpi-label">Simulation Starting Balance (USD)</div>
                <div className="inline-form" style={{ marginTop: 8 }}>
                  <input className="input" type="number" min={1} step={1} value={startingBalance} onChange={(e) => setStartingBalance(e.target.value)} />
                  <button className="btn btn-primary" onClick={() => void saveSettings()} type="button">Save</button>
                </div>
              </div>

              <div className="kpi-card" style={{ marginBottom: 12 }}>
                <div className="kpi-label">API Base Endpoint</div>
                <input className="input" readOnly value={process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"} />
              </div>

              <div className="kpi-card">
                <div className="kpi-label">Current Account Snapshot</div>
                <div className="inline-form" style={{ justifyContent: "space-between", marginTop: 8 }}>
                  <span className="muted">Balance</span>
                  <span>{formatCurrency(status.balance)}</span>
                </div>
                <div className="inline-form" style={{ justifyContent: "space-between", marginTop: 8 }}>
                  <span className="muted">Profit</span>
                  <span className={status.profit >= 0 ? "value-good" : "value-bad"}>{formatCurrency(status.profit)}</span>
                </div>
                <div className="inline-form" style={{ justifyContent: "space-between", marginTop: 8 }}>
                  <span className="muted">Starting Balance</span>
                  <span>{formatCurrency(performance.starting_balance)}</span>
                </div>
              </div>
            </section>

            <section className="card" style={{ gridColumn: "span 4" }}>
              <h3 className="section-title value-bad">Danger Zone</h3>
              <p className="small muted">
                Safe Reset clears paper trading state, open positions, trade history, and re-initializes balance.
              </p>
              <label className="inline-form" style={{ margin: "14px 0" }}>
                <input checked={confirmReset} onChange={(e) => setConfirmReset(e.target.checked)} type="checkbox" />
                <span className="small">I confirm this destructive action</span>
              </label>
              <button className="btn btn-danger" disabled={!confirmReset} onClick={() => void resetAccount()} type="button">
                Execute Safe Reset
              </button>
            </section>
          </div>
        ) : null}
      </TerminalShell>
    </>
  );
}

