export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const DEFAULT_TIMEOUT_MS = 15000;

export class ApiError extends Error {
  constructor(message, { status = 0, data = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request(path, options = {}) {
  const {
    timeout = DEFAULT_TIMEOUT_MS,
    allowStatuses = [],
    headers,
    body,
    ...fetchOptions
  } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      headers,
      body,
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok && !allowStatuses.includes(response.status)) {
      const message = typeof data === "object" && data?.detail
        ? data.detail
        : `Request failed with status ${response.status}`;
      throw new ApiError(message, { status: response.status, data });
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("Request timed out.", { status: 0 });
    }

    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError("Backend is not reachable.", { status: 0 });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function getHealth() {
  return request("/health", { timeout: 4000 });
}

export function getReadiness() {
  return request("/ready", { timeout: 6000, allowStatuses: [503] });
}

export function getModelInfo() {
  return request("/model-info", { timeout: 6000 });
}

export function getDetections() {
  return request("/detections", { timeout: 8000 });
}

export function getDetectionHistory({ limit = 20, status = "all" } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });

  if (status && status !== "all") {
    params.set("status", status);
  }

  return request(`/detections/history?${params.toString()}`, { timeout: 8000 });
}

export function getStats() {
  return request("/stats", { timeout: 8000 });
}

export function getElders({ activeOnly = true } = {}) {
  const params = new URLSearchParams({ active_only: String(activeOnly) });
  return request(`/elders?${params.toString()}`, { timeout: 8000 });
}

export function createElderProfile(payload) {
  return request("/elders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeout: 8000,
  });
}

export function predictVideo(formData) {
  return request("/predict-video", {
    method: "POST",
    body: formData,
    timeout: 120000,
  });
}

export function predictFrame(formData) {
  return request("/predict-frame", {
    method: "POST",
    body: formData,
    timeout: 20000,
  });
}

export function resetLivePrediction() {
  return request("/predict-frame/reset", {
    method: "POST",
    timeout: 8000,
  });
}

export function mockNotify(payload) {
  return request("/mock-notify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    timeout: 8000,
  });
}

export function clearDetections() {
  return request("/detections", {
    method: "DELETE",
    timeout: 8000,
  });
}
