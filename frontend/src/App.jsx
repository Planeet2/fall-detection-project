import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [backendStatus, setBackendStatus] = useState("checking");
  const [modelInfo, setModelInfo] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");
  const [notification, setNotification] = useState(null);

  const allowedFormatsText = useMemo(() => {
    if (!modelInfo?.supported_formats) return ".mp4, .mov, .avi, .webm";
    return modelInfo.supported_formats.join(", ");
  }, [modelInfo]);

  const currentResult = result || stats?.latest_detection || null;
  const currentStatusClass = getStatusClass(currentResult);
  const fallProbability = currentResult?.fall_probability_percent ?? 0;
  const agent = result?.agent || currentResult?.agent || null;

  useEffect(() => {
    checkBackend();
    loadModelInfo();
    loadDashboardData();
  }, []);

  function getStatusText(item) {
    if (!item) return "No analysis";
    if (item.is_fall === true || item.status === "fall") return "Fall detected";
    if (item.status === "warning" || item.risk_level === "medium") return "Warning";
    return "Safe";
  }

  function getStatusClass(item) {
    if (!item) return "idle";
    if (item.is_fall === true || item.risk_level === "high" || item.status === "fall") return "danger";
    if (item.status === "warning" || item.risk_level === "medium") return "warning";
    return "safe";
  }

  async function checkBackend() {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (!response.ok) throw new Error("Backend is not responding");
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    }
  }

  async function loadModelInfo() {
    try {
      const response = await fetch(`${API_URL}/model-info`);
      if (!response.ok) return;
      const data = await response.json();
      setModelInfo(data);
    } catch {
      setModelInfo(null);
    }
  }

  async function loadDashboardData() {
    setHistoryLoading(true);
    try {
      const [detectionsResponse, statsResponse] = await Promise.all([
        fetch(`${API_URL}/detections`),
        fetch(`${API_URL}/stats`),
      ]);

      if (detectionsResponse.ok) {
        const detectionsData = await detectionsResponse.json();
        setDetections(detectionsData.items || []);
      }

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
    } catch {
      setError("Не удалось загрузить историю или статистику.");
    } finally {
      setHistoryLoading(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    setError("");
    setNotification(null);
    setResult(null);
    setSelectedFile(file || null);

    if (videoPreview) URL.revokeObjectURL(videoPreview);
    setVideoPreview(file ? URL.createObjectURL(file) : null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Сначала выбери видеофайл.");
      return;
    }

    setLoading(true);
    setError("");
    setNotification(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${API_URL}/predict-video`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) throw new Error(data.detail || "Ошибка при анализе видео.");

      setResult(data);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Не удалось отправить видео на backend.");
    } finally {
      setLoading(false);
    }
  }

  async function handleMockNotification() {
    const familyMessage = agent?.family_message || "Possible fall detected. Please check immediately.";

    try {
      const response = await fetch(`${API_URL}/mock-notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          elder_id: "elder_001",
          contact_name: "Family member / Caregiver",
          message: familyMessage,
        }),
      });
      const data = await response.json();

      if (!response.ok) throw new Error(data.detail || "Не удалось отправить уведомление.");
      setNotification(data);
    } catch (err) {
      setNotification({ status: "error", message: err.message || "Notification failed" });
    }
  }

  async function handleClearHistory() {
    const confirmClear = window.confirm("Точно очистить историю детекций?");
    if (!confirmClear) return;

    try {
      const response = await fetch(`${API_URL}/detections`, { method: "DELETE" });
      if (!response.ok) throw new Error("Не удалось очистить историю.");
      setResult(null);
      setDetections([]);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Ошибка при очистке истории.");
    }
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
          <a href="#analysis">Video Analysis</a>
          <a href="#agent">Agent Workflow</a>
          <a href="#history">History</a>
          <a href="#privacy">Privacy</a>
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
            <button type="button" className="ghostButton" onClick={loadDashboardData}>Refresh</button>
            <div className={`systemPill ${backendStatus}`}>
              <span />
              {backendStatus === "online" ? "System online" : backendStatus === "offline" ? "Backend offline" : "Checking"}
            </div>
          </div>
        </header>

        <section id="overview" className="heroPanel">
          <div className="heroCopy">
            <div className="statusBadge">AI elderly safety platform</div>
            <h2>Home safety monitoring with fall detection and emergency response workflow.</h2>
            <p>
              Vision model analyzes movement, backend creates structured behavior events,
              and the agent layer decides the next care action.
            </p>

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
            <p>{currentResult?.message || "Upload a video to start safety analysis"}</p>
          </div>
        </section>

        <section className="quickStats">
          <StatCard title="Total checks" value={stats?.total_detections ?? 0} icon="📊" />
          <StatCard title="Falls" value={stats?.fall_detections ?? 0} icon="🚨" tone="danger" />
          <StatCard title="Warnings" value={stats?.warning_detections ?? 0} icon="⚠️" tone="warning" />
          <StatCard title="High risk" value={stats?.high_risk_count ?? 0} icon="🛡️" tone="danger" />
          <StatCard title="Average probability" value={`${stats?.average_fall_probability_percent ?? 0}%`} icon="📈" />
        </section>

        <section id="analysis" className="mainGrid">
          <div className="panel uploadPanel">
            <div className="panelHeader">
              <div>
                <span className="stepTag">01</span>
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
                <span className="uploadIcon">⬆</span>
                <strong>{selectedFile ? selectedFile.name : "Drop or choose a video"}</strong>
                <small>Local backend processing · temporary file removed after analysis</small>
              </label>

              {videoPreview && <video className="videoPreview" src={videoPreview} controls />}

              <button className="primaryButton" type="submit" disabled={!selectedFile || loading}>
                {loading ? "Analyzing video..." : "Run safety analysis"}
              </button>
            </form>

            {loading && (
              <div className="processingCard">
                <span className="spinner" />
                <div>
                  <strong>Model pipeline is running</strong>
                  <p>Extracting pose keypoints and analyzing movement sequence.</p>
                </div>
              </div>
            )}

            {error && <div className="errorBox">{error}</div>}
          </div>

          <div className={`panel resultPanel ${currentStatusClass}`}>
            <div className="panelHeader">
              <div>
                <span className="stepTag">02</span>
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
                  <Info label="Frames" value={currentResult.frames_processed ?? 0} />
                  <Info label="Windows" value={currentResult.windows_analyzed ?? 0} />
                  <Info label="Detection ID" value={currentResult.detection_id || currentResult.id || "—"} />
                  <Info label="Created at" value={currentResult.created_at || "—"} />
                </div>
              </>
            ) : (
              <div className="emptyState">
                <span>🎥</span>
                <strong>No analysis yet</strong>
                <p>Upload a video to see fall probability, risk level, and model details.</p>
              </div>
            )}
          </div>
        </section>

        <section id="agent" className="agentGrid">
          <div className="panel agentPanel">
            <div className="panelHeader">
              <div>
                <span className="stepTag">03</span>
                <h2>Agent Decision / Workflow</h2>
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
              onClick={handleMockNotification}
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
        </section>

        <section className="careGrid">
          <CareCard icon="💊" title="Medicine reminder" text="20:00 · Blood pressure medicine reminder with gentle voice style." />
          <CareCard icon="🌤️" title="Weather care" text="Daily weather reminder before the elder goes outside." />
          <CareCard icon="💬" title="Companion mode" text="Friendly conversation scenario for emotional support and reassurance." />
          <CareCard icon="📞" title="Emergency contact" text={currentResult?.risk_level === "high" ? "Family alert is ready to send." : "Emergency workflow is on standby."} />
        </section>

        <section id="history" className="panel historyPanel">
          <div className="panelHeader">
            <div>
              <span className="stepTag">04</span>
              <h2>Detection History</h2>
            </div>
            <div className="tableActions">
              <button className="ghostButton" type="button" onClick={loadDashboardData}>Refresh</button>
              <button className="dangerButton" type="button" onClick={handleClearHistory} disabled={detections.length === 0}>Clear</button>
            </div>
          </div>

          {historyLoading ? (
            <p className="tableEmpty">Loading history...</p>
          ) : detections.length === 0 ? (
            <p className="tableEmpty">No detections yet.</p>
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
                  {detections.map((item) => (
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
              which makes the workflow easier to audit and safer for elderly-care scenarios.
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

function inferDecision(result) {
  if (!result) return "Waiting for behavior event";
  if (result.risk_level === "high" || result.status === "fall") return "Emergency workflow started";
  if (result.risk_level === "medium" || result.status === "warning") return "Safety confirmation required";
  return "Normal monitoring";
}

function inferNextAction(result) {
  if (!result) return "Upload a video to create a structured behavior event.";
  if (result.risk_level === "high" || result.status === "fall") return "wait_for_elder_confirmation";
  if (result.risk_level === "medium" || result.status === "warning") return "continue_observation";
  return "no_action_required";
}

function inferWorkflowActions(result) {
  if (!result) return ["Waiting for video analysis", "Create structured behavior event", "Run agent decision"];
  if (result.risk_level === "high" || result.status === "fall") {
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
  if (!result) return "The care agent is ready. Please upload a video for analysis.";
  if (result.risk_level === "high" || result.status === "fall") return "A possible fall was detected. Are you okay? Please respond if you need help.";
  if (result.risk_level === "medium" || result.status === "warning") return "Your movement looks unstable. Please take a rest and confirm that you are okay.";
  return "Everything looks normal. Stay safe.";
}

function familyMessage(result) {
  if (!result) return "No emergency message yet.";
  if (result.risk_level === "high" || result.status === "fall") return `Possible fall detected. Fall probability: ${result.fall_probability_percent ?? 0}%. Please check immediately.`;
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

function StatCard({ title, value, icon, tone = "neutral" }) {
  return (
    <div className={`statCard ${tone}`}>
      <span>{icon}</span>
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

function CareCard({ icon, title, text }) {
  return (
    <div className="careCard">
      <span>{icon}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export default App;
