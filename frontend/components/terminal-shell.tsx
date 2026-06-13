import Link from "next/link";
import React from "react";

import type { NavKey } from "../lib/types";
import { formatCurrency } from "../lib/format";

interface TerminalShellProps {
  active: NavKey;
  title: string;
  statusRunning?: boolean;
  balance?: number;
  onKillSwitch?: () => void;
  topRight?: React.ReactNode;
  children: React.ReactNode;
}

const NAV_ITEMS: Array<{ key: NavKey; href: string; icon: string; label: string }> = [
  { key: "overview", href: "/dashboard", icon: "dashboard", label: "Overview" },
  { key: "markets", href: "/markets", icon: "query_stats", label: "Markets" },
  { key: "trades", href: "/trades", icon: "swap_horiz", label: "Trades" },
  { key: "risk", href: "/risk", icon: "gpp_maybe", label: "Risk" },
  { key: "system", href: "/system", icon: "dns", label: "System" },
  { key: "settings", href: "/settings", icon: "settings", label: "Settings" },
];

export function TerminalShell({
  active,
  title,
  statusRunning = false,
  balance,
  onKillSwitch,
  topRight,
  children,
}: TerminalShellProps) {
  return (
    <div className="app-shell">
      <aside className="side-nav">
        <div className="brand-wrap">
          <h1 className="brand-name">POLY-BOT-01</h1>
          <p className="brand-version">V2.4.0-STABLE</p>
        </div>

        <nav className="nav-menu">
          {NAV_ITEMS.map((item) => {
            const isActive = item.key === active;
            return (
              <Link key={item.key} href={item.href} className={`nav-item ${isActive ? "active" : ""}`}>
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="kill-switch-wrap">
          <button className="btn btn-danger" onClick={onKillSwitch} type="button">
            Manual Killswitch
          </button>
        </div>
      </aside>

      <div className="main-shell">
        <header className="top-bar">
          <div className="top-left">
            <h2 className="top-title">{title}</h2>
            <div className="search-shell">
              <span className="material-symbols-outlined">search</span>
              <input placeholder="Search..." readOnly />
            </div>
          </div>

          <div className="top-right">
            <div className={`status-chip ${statusRunning ? "ok" : "warn"}`}>
              <span className="dot" />
              <span>{statusRunning ? "Running" : "Paused"}</span>
            </div>
            <div className="balance-chip">{formatCurrency(balance ?? 0)}</div>
            {topRight}
          </div>
        </header>

        <main className="content-scroll">{children}</main>
      </div>
    </div>
  );
}

