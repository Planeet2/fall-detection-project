import { useCallback, useEffect, useMemo, useState } from "react";

import { getDetectionHistory, getStats } from "../services/api";
import { getStatusClass, getStatusDescription, getStatusText } from "../utils/status";

const FILTERS = [
  { label: "All", value: "all" },
  { label: "Fall", value: "fall" },
  { label: "Suspicious", value: "suspicious" },
  { label: "Normal", value: "normal" },
];

function DetectionHistory({ refreshSignal = 0, onItemsLoaded, onStatsLoaded, onClear }) {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statsError, setStatsError] = useState("");

  const loadHistory = useCallback(async (nextFilter = filter) => {
    setLoading(true);
    setError("");
    setStatsError("");

    try {
      const [historyResult, statsResult] = await Promise.allSettled([
        getDetectionHistory({ limit: 20, status: nextFilter }),
        getStats(),
      ]);

      if (historyResult.status === "fulfilled") {
        const nextItems = historyResult.value.items || [];
        setItems(nextItems);
        onItemsLoaded?.(nextItems);

        if (historyResult.value.storage?.available === false) {
          setError(historyResult.value.storage.error || "Detection history is temporarily unavailable.");
        }
      } else {
        setItems([]);
        onItemsLoaded?.([]);
        setError(historyResult.reason?.message || "Detection history is temporarily unavailable.");
      }

      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
        onStatsLoaded?.(statsResult.value);

        if (statsResult.value.storage?.available === false) {
          setStatsError(statsResult.value.storage.error || "Statistics are temporarily unavailable.");
        }
      } else {
        setStatsError(statsResult.reason?.message || "Statistics are temporarily unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, [filter, onItemsLoaded, onStatsLoaded]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      loadHistory(filter);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [filter, refreshSignal, loadHistory]);

  const summary = useMemo(() => {
    return [
      { label: "Total", value: stats?.total_detections ?? 0 },
      { label: "Fall", value: stats?.fall_detections ?? 0, tone: "danger" },
      { label: "Suspicious", value: stats?.suspicious_detections ?? 0, tone: "warning" },
      { label: "Normal", value: stats?.normal_detections ?? 0, tone: "safe" },
      { label: "Manual review", value: stats?.manual_review_count ?? 0, tone: "warning" },
      { label: "Confirmed", value: stats?.confirmed_fall_count ?? 0, tone: "danger" },
    ];
  }, [stats]);

  return (
    <section id="history" className="panel historyPanel">
      <div className="panelHeader">
        <div>
          <span className="stepTag">History</span>
          <h2>Detection History</h2>
          <p>Stored detection events from PostgreSQL</p>
        </div>
        <div className="tableActions">
          <div className="segmentedControl compactSegments" aria-label="History filter">
            {FILTERS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={filter === item.value ? "active" : ""}
                onClick={() => setFilter(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <button className="ghostButton" type="button" onClick={() => loadHistory(filter)}>
            Refresh
          </button>
          {onClear && (
            <button className="dangerButton" type="button" onClick={onClear} disabled={items.length === 0}>
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="historySummary" aria-label="Detection summary">
        {summary.map((item) => (
          <div key={item.label} className={`historySummaryItem ${item.tone || ""}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>

      {statsError && <div className="historyNotice">{statsError}</div>}
      {error && <div className="errorBox historyError">{error}</div>}

      {loading ? (
        <p className="tableEmpty">Loading detection history...</p>
      ) : items.length === 0 ? (
        <p className="tableEmpty">No detection events for this filter.</p>
      ) : (
        <div className="historyList">
          {items.map((item) => (
            <HistoryCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

function HistoryCard({ item }) {
  const statusClass = getStatusClass(item);
  const agentResult = item.agent_result;
  const elder = item.elder_snapshot || null;

  return (
    <article className={`historyCard ${statusClass}`}>
      <div className="historyCardHeader">
        <div>
          <span className={`statusChip ${statusClass}`}>{getStatusText(item)}</span>
          <h3>{getStatusDescription(item)}</h3>
        </div>
        <time>{formatDate(item.created_at)}</time>
      </div>

      <div className="historyFacts">
        <Fact label="Elder" value={elder?.full_name || item.elder_id || "Not linked"} />
        <Fact label="Room" value={elder?.room || "—"} />
        <Fact label="Risk" value={item.risk_level || "unknown"} />
        <Fact label="Fall probability" value={formatPercent(item.fall_probability_percent)} />
        <Fact label="Mean probability" value={formatPercent(item.mean_fall_probability_percent)} />
        <Fact label="Confirmed fall" value={item.confirmed_fall ? "Yes" : "No"} />
        <Fact label="Manual review" value={item.needs_manual_review ? "Yes" : "No"} />
        <Fact label="Window ratio" value={item.fall_window_ratio ?? "—"} />
      </div>

      <div className="historyReason">
        <span>Reason</span>
        <p>{item.decision_reason || item.message || "No reason recorded."}</p>
      </div>

      {agentResult && (
        <div className="agentResultBox">
          <span>AI Agent</span>
          <div className="historyFacts">
            <Fact label="Risk" value={agentResult.risk_level || "unknown"} />
            <Fact label="Notify caregiver" value={agentResult.notify_caregiver ? "Yes" : "No"} />
          </div>
          <p>{agentResult.message || "No agent message."}</p>
          {agentResult.recommendation && <p><strong>Recommendation:</strong> {agentResult.recommendation}</p>}
          {agentResult.reason && <p><strong>Reason:</strong> {agentResult.reason}</p>}
        </div>
      )}
    </article>
  );
}

function Fact({ label, value }) {
  return (
    <div className="historyFact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatPercent(value) {
  if (value === null || value === undefined) return "—";
  return `${value}%`;
}

function formatDate(value) {
  if (!value) return "No timestamp";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default DetectionHistory;
