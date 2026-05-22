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

  const allowedFormatsText = useMemo(() => {
    if (!modelInfo?.supported_formats) {
      return ".mp4, .mov, .avi, .webm";
    }

    return modelInfo.supported_formats.join(", ");
  }, [modelInfo]);

  useEffect(() => {
    checkBackend();
    loadModelInfo();
    loadDashboardData();
  }, []);

  function getStatusText(item) {
    if (!item) return "NO RESULT";

    if (item.is_fall === true) {
      return "FALL DETECTED";
    }

    if (item.status === "warning") {
      return "WARNING";
    }

    return "SAFE";
  }

  function getStatusClass(item) {
    if (!item) return "";

    if (item.is_fall === true || item.risk_level === "high") {
      return "danger";
    }

    if (item.status === "warning" || item.risk_level === "medium") {
      return "warning";
    }

    return "safe";
  }

  async function checkBackend() {
    try {
      const response = await fetch(`${API_URL}/health`);

      if (!response.ok) {
        throw new Error("Backend is not responding");
      }

      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    }
  }

  async function loadModelInfo() {
    try {
      const response = await fetch(`${API_URL}/model-info`);

      if (!response.ok) {
        return;
      }

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
    setResult(null);
    setSelectedFile(file || null);

    if (videoPreview) {
      URL.revokeObjectURL(videoPreview);
    }

    if (file) {
      setVideoPreview(URL.createObjectURL(file));
    } else {
      setVideoPreview(null);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Сначала выбери видеофайл.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${API_URL}/predict-video`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка при анализе видео.");
      }

      setResult(data);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Не удалось отправить видео на backend.");
    } finally {
      setLoading(false);
    }
  }

  async function handleClearHistory() {
    const confirmClear = window.confirm("Точно очистить историю детекций?");

    if (!confirmClear) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/detections`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Не удалось очистить историю.");
      }

      setResult(null);
      setDetections([]);
      await loadDashboardData();
    } catch (err) {
      setError(err.message || "Ошибка при очистке истории.");
    }
  }

  const currentResult = result || stats?.latest_detection;

  return (
    <main className="app">
      <section className="hero">
        <div>
          <p className="eyebrow">AI Fall Detection System</p>
          <h1>Eldery Camera Check</h1>
          <p className="heroText">
            Система анализирует видео, находит скелет человека через YOLOv8 Pose
            и определяет вероятность падения с помощью LSTM-модели.
          </p>
        </div>

        <div className={`backendStatus ${backendStatus}`}>
          <span className="dot" />
          Backend:{" "}
          {backendStatus === "online"
            ? "online"
            : backendStatus === "offline"
            ? "offline"
            : "checking"}
        </div>
      </section>

      <section className="grid">
        <div className="card uploadCard">
          <h2>1. Загрузите видео</h2>
          <p className="muted">Поддерживаемые форматы: {allowedFormatsText}</p>

          <form onSubmit={handleSubmit}>
            <label className="fileInput">
              <input
                type="file"
                accept=".mp4,.mov,.avi,.webm,video/mp4,video/quicktime,video/x-msvideo,video/webm"
                onChange={handleFileChange}
              />
              <span>
                {selectedFile ? selectedFile.name : "Выбрать видео"}
              </span>
            </label>

            {videoPreview && (
              <video className="preview" src={videoPreview} controls />
            )}

            <button
              className="primaryButton"
              type="submit"
              disabled={!selectedFile || loading}
            >
              {loading ? "Анализируем..." : "Analyze Video"}
            </button>
          </form>

          {loading && (
            <div className="loadingBox">
              <span className="spinner" />
              <div>
                <strong>Видео анализируется...</strong>
                <p>Backend обрабатывает кадры и запускает модель.</p>
              </div>
            </div>
          )}

          {error && <div className="errorBox">{error}</div>}
        </div>

        <div className={`card resultCard ${getStatusClass(currentResult)}`}>
          <h2>2. Результат анализа</h2>

          {currentResult ? (
            <>
              <div className="resultLabel">{getStatusText(currentResult)}</div>

              <p className="message">
                {currentResult.message || "Последняя сохранённая проверка"}
              </p>

              <div className="probability">
                <span>Вероятность падения</span>
                <strong>
                  {currentResult.fall_probability_percent ?? 0}%
                </strong>
              </div>

              <div className="progress">
                <div
                  style={{
                    width: `${Math.min(
                      currentResult.fall_probability_percent || 0,
                      100
                    )}%`,
                  }}
                />
              </div>

              <div className="details">
                <div>
                  <span>Risk level</span>
                  <strong>{currentResult.risk_level || "unknown"}</strong>
                </div>

                <div>
                  <span>Status</span>
                  <strong>{currentResult.status || "unknown"}</strong>
                </div>

                <div>
                  <span>Frames processed</span>
                  <strong>{currentResult.frames_processed ?? 0}</strong>
                </div>

                <div>
                  <span>Windows analyzed</span>
                  <strong>{currentResult.windows_analyzed ?? 0}</strong>
                </div>

                <div>
                  <span>Detection ID</span>
                  <strong>
                    {currentResult.detection_id || currentResult.id || "—"}
                  </strong>
                </div>

                <div>
                  <span>Created at</span>
                  <strong>{currentResult.created_at || "—"}</strong>
                </div>
              </div>
            </>
          ) : (
            <div className="emptyResult">
              <div className="cameraIcon">🎥</div>
              <p>Загрузите видео и нажмите Analyze Video.</p>
            </div>
          )}
        </div>
      </section>

      <section className="statsGrid">
        <StatCard title="Всего проверок" value={stats?.total_detections ?? 0} />
        <StatCard title="Падений" value={stats?.fall_detections ?? 0} />
        <StatCard title="Безопасных" value={stats?.safe_detections ?? 0} />
        <StatCard
          title="Предупреждений"
          value={stats?.warning_detections ?? 0}
        />
        <StatCard title="High risk" value={stats?.high_risk_count ?? 0} />
        <StatCard
          title="Средняя вероятность"
          value={`${stats?.average_fall_probability_percent ?? 0}%`}
        />
      </section>

      <section className="card historyCard">
        <div className="historyHeader">
          <div>
            <h2>3. История детекций</h2>
            <p className="muted">
              Backend сохраняет последние проверки в журнал детекций.
            </p>
          </div>

          <div className="historyActions">
            <button
              className="secondaryButton"
              type="button"
              onClick={loadDashboardData}
            >
              Обновить
            </button>

            <button
              className="dangerButton"
              type="button"
              onClick={handleClearHistory}
              disabled={detections.length === 0}
            >
              Очистить
            </button>
          </div>
        </div>

        {historyLoading ? (
          <p className="empty">Загружаем историю...</p>
        ) : detections.length === 0 ? (
          <p className="empty">История пока пустая.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Файл</th>
                  <th>Статус</th>
                  <th>Риск</th>
                  <th>Вероятность</th>
                  <th>Кадры</th>
                </tr>
              </thead>

              <tbody>
                {detections.map((item) => (
                  <tr key={item.id}>
                    <td>{item.created_at}</td>
                    <td>{item.filename}</td>
                    <td>
                      <span className={`badge ${getStatusClass(item)}`}>
                        {getStatusText(item)}
                      </span>
                    </td>
                    <td>{item.risk_level || "—"}</td>
                    <td>{item.fall_probability_percent ?? 0}%</td>
                    <td>{item.frames_processed ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

<section className="infoGrid">
  <div className="card patientCard">
    <h2>Patient Monitoring</h2>
    <p className="muted">
      Система может использоваться для наблюдения за пожилым человеком дома,
      в палате или в care center.
    </p>

    <div className="monitorList">
      <div>
        <span className="monitorIcon">👤</span>
        <div>
          <strong>Patient status</strong>
          <p>{currentResult?.is_fall ? "Possible fall detected" : "Normal activity"}</p>
        </div>
      </div>

      <div>
        <span className="monitorIcon">📹</span>
        <div>
          <strong>Video analysis</strong>
          <p>YOLOv8 Pose extracts body keypoints from uploaded video.</p>
        </div>
      </div>

      <div>
        <span className="monitorIcon">🧠</span>
        <div>
          <strong>AI decision</strong>
          <p>LSTM model analyzes movement sequence and estimates fall risk.</p>
        </div>
      </div>
    </div>
  </div>

  <div className="card emergencyCard">
    <h2>Emergency Contact</h2>
    <p className="muted">
      При высоком риске система может уведомить родственника или оператора.
    </p>

    <div className="contactBox">
      <div>
        <span>Contact person</span>
        <strong>Family member / Caregiver</strong>
      </div>

      <div>
        <span>Alert rule</span>
        <strong>
          {currentResult?.risk_level === "high"
            ? "High risk alert required"
            : "No emergency alert"}
        </strong>
      </div>

      <button
        className={currentResult?.risk_level === "high" ? "alertButton active" : "alertButton"}
        type="button"
      >
        {currentResult?.risk_level === "high"
          ? "Emergency Alert Ready"
          : "Emergency Alert Standby"}
      </button>
    </div>
  </div>

  <div className="card systemCard">
    <h2>System Status</h2>
    <p className="muted">
      Техническое состояние frontend, backend и модели.
    </p>

    <div className="statusList">
      <div>
        <span className={`statusDot ${backendStatus === "online" ? "green" : "red"}`} />
        <strong>Backend API</strong>
        <p>{backendStatus}</p>
      </div>

      <div>
        <span className="statusDot green" />
        <strong>Frontend</strong>
        <p>React + Vite running</p>
      </div>

      <div>
        <span className={modelInfo ? "statusDot green" : "statusDot red"} />
        <strong>AI Model</strong>
        <p>{modelInfo?.model || "Not loaded"}</p>
      </div>

      <div>
        <span className="statusDot green" />
        <strong>Detection Log</strong>
        <p>{detections.length} saved records</p>
      </div>
    </div>
  </div>

  <div className="card privacyCard">
    <h2>Privacy / Local Processing</h2>
    <p>
      Видео отправляется только на локальный backend проекта. После обработки
      временный файл удаляется, а в истории сохраняются только результаты
      анализа: имя файла, вероятность падения, риск, количество кадров и время
      проверки.
    </p>

    <div className="privacyBadges">
      <span>Local backend</span>
      <span>No cloud upload</span>
      <span>Temporary video file</span>
      <span>Result log only</span>
    </div>
  </div>

  <div className="card modelCard">
    <h2>Model Information</h2>
    <p className="muted">Данные загружаются из backend `/model-info`.</p>

    <div className="details single">
      <div>
        <span>Model</span>
        <strong>{modelInfo?.model || "—"}</strong>
      </div>

      <div>
        <span>Input</span>
        <strong>{modelInfo?.input || "—"}</strong>
      </div>

      <div>
        <span>Sequence length</span>
        <strong>{modelInfo?.sequence_length || "—"}</strong>
      </div>

      <div>
        <span>Threshold</span>
        <strong>{modelInfo?.threshold || "—"}</strong>
      </div>

      <div>
        <span>Classes</span>
        <strong>{modelInfo?.classes?.join(", ") || "—"}</strong>
      </div>
    </div>
  </div>
</section>
    </main>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="statCard">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;