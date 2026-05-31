export function getStatusClass(item) {
  if (!item) return "idle";
  if (item.confirmed_fall === true || item.is_fall === true || item.status === "fall") return "danger";
  if (item.status === "suspicious" || item.needs_manual_review === true) return "warning";
  if (item.status === "warning" || item.risk_level === "medium") return "warning";
  if (item.status === "collecting" || item.status === "no_person") return "collecting";
  return "safe";
}

export function getStatusText(item) {
  if (!item) return "No analysis";
  if (item.confirmed_fall === true || item.is_fall === true || item.status === "fall") return "Confirmed fall";
  if (item.status === "suspicious" || item.needs_manual_review === true) return "Suspicious";
  if (item.status === "normal") return "Normal";
  if (item.status === "warning" || item.risk_level === "medium") return "Warning";
  if (item.status === "collecting") return "Collecting";
  if (item.status === "no_person") return "No reliable pose";
  return "Safe";
}

export function getStatusDescription(item) {
  if (!item) return "No event selected.";
  if (item.confirmed_fall === true || item.is_fall === true || item.status === "fall") {
    return "Confirmed fall detected. Emergency workflow started.";
  }
  if (item.status === "suspicious" || item.needs_manual_review === true) {
    return "Possible fall-like movement. Manual review recommended.";
  }
  if (item.status === "normal" || item.status === "safe") {
    return "No fall detected.";
  }
  if (item.status === "no_person") {
    return "No reliable person pose detected.";
  }
  if (item.status === "collecting") {
    return "Collecting reliable live frames.";
  }
  return item.message || "Event recorded.";
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
