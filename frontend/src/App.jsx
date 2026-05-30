import { useEffect, useMemo, useState } from "react";

import LiveCamera from "./components/LiveCamera";
import {
  API_URL,
  clearDetections,
  getDetections,
  getHealth,
  getModelInfo,
  getReadiness,
  getStats,
  mockNotify,
  predictVideo,
} from "./services/api";
import { formatCheck, getReadinessClass, getStatusClass, getStatusText } from "./utils/status";
import "./App.css";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [readiness, setReadiness] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [liveResult, setLiveResult] = useState(null);
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");
  const [notification, setNotification] = useState(null);
  const [historyFilter, setHistoryFilter] = useState("all");

  const allowedFormatsText = useMemo(() => {
    if (!modelInfo?.supported_formats) return ".mp4, .mov, .avi, .webm";
    return modelInfo.supported_formats.join(", ");
  }, [modelInfo]);

  const filteredDetections = useMemo(() => {
    if (historyFilter === "all") return detections;
    if (historyFilter === "fall") {
      return detections.filter((item) => item.confirmed_fall === true || item.is_fall === true || item.status === "fall");
    }
    if (historyFilter === "safe") {
      return detections.filter((item) => item.status === "safe" || item.status === "normal" || item.risk_level === "low");
    }
    if (historyFilter === "warning") {
      return detections.filter((item) => item.status === "warning" || item.status === "suspicious" || item.risk_level === "medium");
    }
    return detections.filter((item) => item.status === historyFilter || item.risk_level === historyFilter);
  }, [detections, historyFilter]);

  const currentResult = liveResult || result || stats?.latest_detection || null;
  const currentStatusClass = getStatusClass(currentResult);
  const readinessClass = getReadinessClass(readiness, backendStatus);
  const fallProbability = currentResult?.fall_probability_percent ?? 0;
  const agent = liveResult?.agent || result?.agent || currentResult?.agent || null;
  const isBackendOffline = backendStatus === "offline";

  useEffect(() => {
    refreshSystem();
    loadModelInfo();
    loadDashboardData();
  }, []);

  useEffect(() => {
    return () => {
      if (videoPreview) URL.revokeObjectURL(videoPreview);
    };
  }, [videoPreview]);

  async function refreshSystem() {
    setBackendStatus("checking");

    try {
      await getHealth();
      setBackendStatus("online");
      const readinessData = await getReadiness();
      setReadiness(readinessData);
    } catch {
      setBackendStatus("offline");
      setReadiness(null);
    }
  }

  async function loadModelInfo() {
    try {
      const data = await getModelInfo();
      setModelInfo(data);
    } catch {
      setModelInfo(null);
    }
  }

  async function loadDashboardData() {
    setHistoryLoading(true);

    try {
      const [detectionsResult, statsResult] = await Promise.allSettled([
        getDetections(),
        getStats(),
      ]);

      if (detectionsResult.status === "fulfilled") {
        setDetections(detectionsResult.value.items || []);
      }

      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }

      if (detectionsResult.status === "rejected" || statsResult.status === "rejected") {
        setError("History or statistics are temporarily unavailable.");
      }
    } finally {
      setHistoryLoading(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    setError("");
    setNotification(null);
    setResult(null);
    setLiveResult(null);
    setSelectedFile(file || null);
    setVideoPreview(file ? URL.createObjectURL(file) : null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Choose a video file first.");
      return;
    }

    setLoading(true);
    setError("");
    setNotification(null);
    setResult(null);
    setLiveResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const data = await predictVideo(formData);
      setResult(data);

      if (data.storage?.saved === false) {
        setError(`Analysis completed, but history was not saved: ${data.storage.error}`);
      }

      await loadDashboardData();
      await refreshSystem();
    } catch (err) {
      setError(err.message || "Could not analyze video.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMockNotification() {
    const familyMessage = agent?.family_message || "Possible fall detected. Please check immediately.";

    try {
      const data = await mockNotify({
        elder_id: "elder_001",
        contact_name: "Family member / Caregiver",
        message: familyMessage,
      });
      setNotification(data);
    } catch (err) {
      setNotification({ status: "error", message: err.message || "Notification failed" });
    }
  }

  async function handleClearHistory() {
    const confirmClear = window.confirm("Clear detection history?");
    if (!confirmClear) return;

    try {
      await clearDetections();
      setResult(null);
      setDetections([]);
      await loadDashboardData();
      await refreshSystem();
    } catch (err) {
      setError(err.message || "Could not clear detection history.");
    }
  }

  async function handleRefresh() {
    setError("");
    await Promise.all([refreshSystem(), loadModelInfo(), loadDashboardData()]);
  }

  return (
    <main className="productShell">
      <aside className="sidebar">
        <div className="brandBlock">
          <div className="brandIcon">EG</div>
          <div>
            <strong>ElderGuard</strong>
            <span>Care Agent</span>
          </div>
        </div>

        <nav className="sideNav" aria-label="Dashboard navigation">
          <a href="#overview" className="active">Overview</a>
          <a href="#live">Live Camera</a>
          <a href="#analysis">Video Analysis</a>
          <a href="#agent">Workflow</a>
          <a href="#history">History</a>
        </nav>

        <div className="sideFooter">
          <span className={`liveDot ${backendStatus}`} />
          <div>
            <strong>Backend API</strong>
            <p>{backendStatus}</p>
          </div>
        </div>
      </aside>

      <section className="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">元景万悟 · 银发守护智能体</p>
            <h1>ElderGuard Agent</h1>
          </div>

          <div className="topActions">
            <button type="button" className="ghostButton" onClick={handleRefresh}>Refresh</button>
            <div className={`systemPill ${readinessClass}`}>
              <span />
              {readiness?.status === "ready" ? "Ready" : backendStatus === "offline" ? "Offline" : "Degraded"}
            </div>
          </div>
        </header>

        <section id="overview" className="overviewBand">
          <div className="overviewMain">
            <div className="statusBadge">Safety dashboard</div>
            <h2>Live camera monitoring, video analysis, and emergency workflow in one operator view.</h2>
            <div className="heroMetrics">
              <Metric label="Current risk" value={currentResult?.risk_level || "—"} tone={currentStatusClass} />
              <Metric label="Fall probability" value={`${fallProbability}%`} tone={currentStatusClass} />
              <Metric label="Saved events" value={detections.length} />
            </div>
          </div>

          <div className={`riskDial ${currentStatusClass}`}>
            <div className="riskRing" style={{ "--value": `${Math.min(fallProbability, 100) * 3.6}deg` }}>
              <div>
                <strong>{fallProbability}%</strong>
                <span>{getStatusText(currentResult)}</span>
              </div>
            </div>
            <p>{currentResult?.message || "Waiting for live or video analysis"}</p>
          </div>
        </section>

        <section className="systemGrid">
          <SystemCard title="API" value={backendStatus} tone={backendStatus === "online" ? "safe" : "danger"} detail={API_URL} />
          <SystemCard title="Model" value={formatCheck(readiness?.checks?.model)} tone={readiness?.checks?.model?.ok ? "safe" : "warning"} />
          <SystemCard title="Storage" value={formatCheck(readiness?.checks?.storage)} tone={readiness?.checks?.storage?.ok ? "safe" : "warning"} />
          <SystemCard title="Sequence" value={modelInfo?.sequence_length || "—"} detail="frames" />
        </section>

        <section className="quickStats">
          <StatCard title="Total checks" value={stats?.total_detections ?? 0} token="T" />
          <StatCard title="Falls" value={stats?.fall_detections ?? 0} token="F" tone="danger" />
          <StatCard title="Warnings" value={stats?.warning_detections ?? 0} token="W" tone="warning" />
          <StatCard title="High risk" value={stats?.high_risk_count ?? 0} token="H" tone="danger" />
          <StatCard title="Average probability" value={`${stats?.average_fall_probability_percent ?? 0}%`} token="P" />
        </section>

        <LiveCamera disabled={isBackendOffline} onResult={setLiveResult} />

        <section id="analysis" className="mainGrid">
          <div className="panel uploadPanel">
            <div className="panelHeader">
              <div>
                <span className="stepTag">Video</span>
                <h2>Video Analysis</h2>
              </div>
              <p>{allowedFormatsText}</p>
            </div>

            <form onSubmit={handleSubmit}>
              <label className="dropZone">
                <input
                  type="file"
                  accept=".mp4,.mov,.avi,.webm,video/mp4,video/quicktime,video/x-msvideo,video/webm"
                  onChange={handleFileChange}
                />
                <span className="uploadIcon">UP</span>
                <strong>{selectedFile ? selectedFile.name : "Choose a video"}</strong>
                <small>Temporary upload · local analysis</small>
              </label>

              {videoPreview && <video className="videoPreview" src={videoPreview} controls />}

              <button className="primaryButton" type="submit" disabled={!selectedFile || loading || isBackendOffline}>
                {loading ? "Analyzing..." : "Run analysis"}
              </button>
            </form>

            {loading && (
              <div className="processingCard">
                <span className="spinner" />
                <div>
                  <strong>Analysis running</strong>
                  <p>Pose keypoints and movement sequence are being processed.</p>
                </div>
              </div>
            )}

            {error && <div className="errorBox">{error}</div>}
          </div>

          <ResultPanel currentResult={currentResult} currentStatusClass={currentStatusClass} fallProbability={fallProbability} />
        </section>

        <section id="agent" className="agentGrid">
          <AgentPanel agent={agent} currentResult={currentResult} />
          <CommunicationPanel
            agent={agent}
            currentResult={currentResult}
            notification={notification}
            onNotify={handleMockNotification}
          />
        </section>

        <section className="careGrid">
          <CareCard token="Rx" title="Medicine reminder" text="20:00 · Blood pressure medicine reminder with gentle voice style." />
          <CareCard token="Wx" title="Weather care" text="Daily weather reminder before the elder goes outside." />
          <CareCard token="Chat" title="Companion mode" text="Friendly conversation scenario for emotional support and reassurance." />
          <CareCard token="SOS" title="Emergency contact" text={currentResult?.risk_level === "high" ? "Family alert is ready to send." : "Emergency workflow is on standby."} />
        </section>

        <section id="history" className="panel historyPanel">
          <div className="panelHeader">
            <div>
              <span className="stepTag">History</span>
              <h2>Detection History</h2>
            </div>
            <div className="tableActions">
              <div className="segmentedControl compactSegments" aria-label="History filter">
                {["all", "safe", "warning", "fall"].map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    className={historyFilter === filter ? "active" : ""}
                    onClick={() => setHistoryFilter(filter)}
                  >
                    {filter}
                  </button>
                ))}
              </div>
              <button className="ghostButton" type="button" onClick={loadDashboardData}>Refresh</button>
              <button className="dangerButton" type="button" onClick={handleClearHistory} disabled={detections.length === 0}>Clear</button>
            </div>
          </div>

          {historyLoading ? (
            <p className="tableEmpty">Loading history...</p>
          ) : filteredDetections.length === 0 ? (
            <p className="tableEmpty">No matching detections.</p>
          ) : (
            <div className="tableWrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>File</th>
                    <th>Status</th>
                    <th>Risk</th>
                    <th>Probability</th>
                    <th>Agent</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDetections.map((item) => (
                    <tr key={item.id}>
                      <td>{item.created_at}</td>
                      <td>{item.filename}</td>
                      <td><span className={`statusChip ${getStatusClass(item)}`}>{getStatusText(item)}</span></td>
                      <td>{item.risk_level || "—"}</td>
                      <td>{item.fall_probability_percent ?? 0}%</td>
                      <td>{item.agent_decision || item.agent?.decision || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section id="privacy" className="bottomGrid">
          <div className="panel privacyPanel">
            <h2>Privacy & Safety</h2>
            <p>
              Raw video is processed by the local backend. The agent receives only structured behavior events,
              which keeps the workflow easier to audit.
            </p>
            <div className="badgeList">
              <span>Local backend</span>
              <span>No raw video to agent</span>
              <span>Structured event only</span>
              <span>Sensitive action confirmation</span>
            </div>
          </div>

          <div className="panel modelPanel">
            <h2>Model & API</h2>
            <div className="detailGrid compact">
              <Info label="Model" value={modelInfo?.model || "—"} />
              <Info label="Input" value={modelInfo?.input || "—"} />
              <Info label="Sequence" value={modelInfo?.sequence_length || "—"} />
              <Info label="Threshold" value={modelInfo?.threshold || "—"} />
              <Info label="Classes" value={modelInfo?.classes?.join(", ") || "—"} />
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

function ResultPanel({ currentResult, currentStatusClass, fallProbability }) {
  return (
    <div className={`panel resultPanel ${currentStatusClass}`}>
      <div className="panelHeader">
        <div>
          <span className="stepTag">Result</span>
          <h2>Safety Result</h2>
        </div>
        <span className={`statusChip ${currentStatusClass}`}>{getStatusText(currentResult)}</span>
      </div>

      {currentResult ? (
        <>
          <div className="resultHero">
            <strong>{fallProbability}%</strong>
            <span>fall probability</span>
          </div>

          <div className="progressTrack">
            <div style={{ width: `${Math.min(fallProbability, 100)}%` }} />
          </div>

          <div className="detailGrid">
            <Info label="Risk level" value={currentResult.risk_level || "unknown"} />
            <Info label="Status" value={currentResult.status || "unknown"} />
            <Info label="Frames" value={currentResult.frames_processed ?? currentResult.frames_collected ?? 0} />
            <Info label="Windows" value={currentResult.windows_analyzed ?? currentResult.smoothing_window ?? 0} />
            <Info label="Detection ID" value={currentResult.detection_id || currentResult.id || "—"} />
            <Info label="Created at" value={currentResult.created_at || "—"} />
          </div>
        </>
      ) : (
        <div className="emptyState">
          <strong>No analysis yet</strong>
          <p>Live and video results will appear here.</p>
        </div>
      )}
    </div>
  );
}

function AgentPanel({ agent, currentResult }) {
  return (
    <div className="panel agentPanel">
      <div className="panelHeader">
        <div>
          <span className="stepTag">Agent</span>
          <h2>Decision Workflow</h2>
        </div>
        <span className="yuanjingTag">Yuanjing Wanwu prototype</span>
      </div>

      <div className="decisionCard">
        <span>Decision</span>
        <strong>{agent?.decision_label || agent?.decision || inferDecision(currentResult)}</strong>
        <p>{agent?.next_action || inferNextAction(currentResult)}</p>
      </div>

      <div className="workflowTimeline">
        {(agent?.actions || inferWorkflowActions(currentResult)).map((action, index) => (
          <div key={`${action}-${index}`} className="workflowStep">
            <span>{index + 1}</span>
            <p>{action}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CommunicationPanel({ agent, currentResult, notification, onNotify }) {
  return (
    <div className="panel messagePanel">
      <h2>Care Communication</h2>
      <div className="messageBubble elder">
        <span>Message to elder</span>
        <p>{agent?.elder_message || elderMessage(currentResult)}</p>
      </div>

      <div className="messageBubble family">
        <span>Message to family</span>
        <p>{agent?.family_message || familyMessage(currentResult)}</p>
      </div>

      <button
        type="button"
        className="notifyButton"
        onClick={onNotify}
        disabled={!currentResult || currentResult?.risk_level !== "high"}
      >
        Send mock family notification
      </button>

      {notification && (
        <div className={`notificationBox ${notification.status === "error" ? "error" : "success"}`}>
          <strong>{notification.status === "error" ? "Notification failed" : "Notification sent"}</strong>
          <p>{notification.message || notification.sent_at || notification.channel}</p>
        </div>
      )}
    </div>
  );
}

function inferDecision(result) {
  if (!result) return "Waiting for behavior event";
  if (result.status === "no_person") return "Searching for reliable pose";
  if (result.status === "collecting") return "Collecting live frames";
  if (result.status === "suspicious" || result.needs_manual_review === true) return "Manual review required";
  if (result.confirmed_fall === true || result.status === "fall") return "Emergency workflow started";
  if (result.risk_level === "medium" || result.status === "warning") return "Safety confirmation required";
  return "Normal monitoring";
}

function inferNextAction(result) {
  if (!result) return "wait_for_event";
  if (result.status === "no_person") return "continue_pose_tracking";
  if (result.status === "collecting") return "continue_collecting_frames";
  if (result.status === "suspicious" || result.needs_manual_review === true) return "review_video";
  if (result.confirmed_fall === true || result.status === "fall") return "wait_for_elder_confirmation";
  if (result.risk_level === "medium" || result.status === "warning") return "continue_observation";
  return "no_action_required";
}

function inferWorkflowActions(result) {
  if (!result) return ["Wait for live or uploaded video", "Create structured event", "Run agent decision"];
  if (result.status === "no_person") return ["Ignore low-quality frame", "Keep searching for reliable pose", "Reset buffer if tracking is lost"];
  if (result.status === "collecting") return ["Collect reliable pose frames", "Wait for full sequence", "Hold emergency workflow"];
  if (result.status === "suspicious" || result.needs_manual_review === true) {
    return ["Manual review recommended", "No emergency workflow started", "Continue observation"];
  }
  if (result.confirmed_fall === true || result.status === "fall") {
    return [
      "Voice confirmation requested",
      "Family notification prepared",
      "Incident report generated",
      "Event saved to detection log",
    ];
  }
  if (result.risk_level === "medium" || result.status === "warning") {
    return ["Ask elder for confirmation", "Suggest rest or health check", "Continue observation"];
  }
  return ["Save normal event", "Continue passive monitoring"];
}

function elderMessage(result) {
  if (!result) return "The care agent is ready.";
  if (result.status === "no_person") return "Please stay within the camera view.";
  if (result.status === "collecting") return "The system is stabilizing live movement detection.";
  if (result.status === "suspicious" || result.needs_manual_review === true) return "A fall-like movement was detected. Please confirm that you are safe.";
  if (result.confirmed_fall === true || result.status === "fall") return "A possible fall was detected. Are you okay? Please respond if you need help.";
  if (result.risk_level === "medium" || result.status === "warning") return "Your movement looks unstable. Please take a rest and confirm that you are okay.";
  return "Everything looks normal. Stay safe.";
}

function familyMessage(result) {
  if (!result) return "No emergency message yet.";
  if (result.status === "suspicious" || result.needs_manual_review === true) return "A suspicious movement was detected. Manual review is recommended.";
  if (result.confirmed_fall === true || result.status === "fall") return `Possible fall detected. Fall probability: ${result.fall_probability_percent ?? 0}%. Please check immediately.`;
  if (result.risk_level === "medium" || result.status === "warning") return "A warning-level movement event was detected. Please continue observation.";
  return "No emergency alert is required.";
}

function Metric({ label, value, tone = "neutral" }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SystemCard({ title, value, detail, tone = "neutral" }) {
  return (
    <div className={`systemCard ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      {detail && <p>{detail}</p>}
    </div>
  );
}

function StatCard({ title, value, token, tone = "neutral" }) {
  return (
    <div className={`statCard ${tone}`}>
      <span>{token}</span>
      <div>
        <p>{title}</p>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="infoItem">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CareCard({ token, title, text }) {
  return (
    <div className="careCard">
      <span>{token}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export default App;
