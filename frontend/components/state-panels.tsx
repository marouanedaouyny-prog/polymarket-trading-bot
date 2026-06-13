import React from "react";

export function LoadingPanel({ label = "Loading" }: { label?: string }) {
  return (
    <div className="card">
      <p className="muted">{label}...</p>
    </div>
  );
}

export function ErrorPanel({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card alert-critical">
      <p>{message}</p>
      {onRetry ? (
        <button className="btn btn-primary" onClick={onRetry} type="button">
          Retry
        </button>
      ) : null}
    </div>
  );
}

