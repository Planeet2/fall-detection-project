export function getStatusClass(item) {
  if (!item) return "idle";
  if (item.is_fall === true || item.risk_level === "high" || item.status === "fall") return "danger";
  if (item.status === "warning" || item.risk_level === "medium") return "warning";
  if (item.status === "collecting" || item.status === "no_person") return "collecting";
  return "safe";
}

export function getStatusText(item) {
  if (!item) return "No analysis";
  if (item.is_fall === true || item.status === "fall") return "Fall detected";
  if (item.status === "warning" || item.risk_level === "medium") return "Warning";
  if (item.status === "collecting") return "Collecting";
  if (item.status === "no_person") return "No reliable pose";
  return "Safe";
}

export function getReadinessClass(readiness, backendStatus) {
  if (backendStatus === "offline") return "danger";
  if (!readiness) return "idle";
  if (readiness.status === "ready") return "safe";
  return "warning";
}

export function formatCheck(check) {
  if (!check) return "unknown";
  if (check.ok) return check.loaded === false ? "ready on demand" : "ready";
  return check.error || "unavailable";
}
