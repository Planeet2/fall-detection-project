import { useEffect, useRef, useState } from "react";

import { predictFrame, resetLivePrediction } from "../services/api";
import { getStatusClass, getStatusText } from "../utils/status";

const DEFAULT_FPS = 4;

function LiveCamera({ disabled = false, onResult }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const sendingRef = useRef(false);
  const [isRunning, setIsRunning] = useState(false);
  const [fps, setFps] = useState(DEFAULT_FPS);
  const [liveResult, setLiveResult] = useState(null);
  const [cameraError, setCameraError] = useState("");

  useEffect(() => {
    return () => {
      window.clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  async function startCamera() {
    setCameraError("");

    try {
      await resetLivePrediction();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 960 },
          height: { ideal: 540 },
          facingMode: "user",
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsRunning(true);
      setLiveResult(null);
      onResult(null);
      startFrameLoop(fps);
    } catch (error) {
      setCameraError(error.message || "Could not start camera.");
      stopCamera();
    }
  }

  async function stopCamera() {
    window.clearInterval(timerRef.current);
    timerRef.current = null;
    sendingRef.current = false;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }

    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsRunning(false);

    try {
      await resetLivePrediction();
    } catch {
      // The backend may already be offline; local camera cleanup should still finish.
    }
  }

  async function resetLiveState() {
    setCameraError("");
    setLiveResult(null);
    onResult(null);

    try {
      await resetLivePrediction();
    } catch (error) {
      setCameraError(error.message || "Could not reset live state.");
    }
  }

  function startFrameLoop(nextFps) {
    window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      captureAndSendFrame();
    }, Math.round(1000 / nextFps));
  }

  function setFrameRate(nextFps) {
    setFps(nextFps);

    if (isRunning) {
      startFrameLoop(nextFps);
    }
  }

  async function captureAndSendFrame() {
    if (sendingRef.current || !videoRef.current || !canvasRef.current) return;
    if (videoRef.current.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;

    sendingRef.current = true;

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const width = video.videoWidth || 640;
      const height = video.videoHeight || 360;

      canvas.width = width;
      canvas.height = height;
      canvas.getContext("2d").drawImage(video, 0, 0, width, height);

      const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, "image/jpeg", 0.82);
      });

      if (!blob) return;

      const formData = new FormData();
      formData.append("file", blob, "live-frame.jpg");

      const result = await predictFrame(formData);
      setLiveResult(result);
      onResult(result);
    } catch (error) {
      setCameraError(error.message || "Live prediction failed.");
    } finally {
      sendingRef.current = false;
    }
  }

  const statusClass = getStatusClass(liveResult);
  const pose = liveResult?.pose || {};

  return (
    <section id="live" className={`panel livePanel ${statusClass}`}>
      <div className="panelHeader">
        <div>
          <span className="stepTag">Live</span>
          <h2>Live Camera</h2>
        </div>
        <span className={`statusChip ${statusClass}`}>{getStatusText(liveResult)}</span>
      </div>

      <div className="liveGrid">
        <div className="cameraStage">
          <video ref={videoRef} className="cameraVideo" playsInline muted />
          {!isRunning && (
            <div className="cameraPlaceholder">
              <strong>Camera stopped</strong>
              <span>Live result will appear here</span>
            </div>
          )}
          <canvas ref={canvasRef} className="captureCanvas" />
        </div>

        <div className="liveControls">
          <div className="segmentedControl" aria-label="Live frame rate">
            {[4, 6, 8].map((value) => (
              <button
                key={value}
                type="button"
                className={fps === value ? "active" : ""}
                onClick={() => setFrameRate(value)}
              >
                {value} fps
              </button>
            ))}
          </div>

          <div className="buttonRow">
            <button
              type="button"
              className="primaryButton compactButton"
              onClick={startCamera}
              disabled={disabled || isRunning}
            >
              Start
            </button>
            <button
              type="button"
              className="ghostButton"
              onClick={stopCamera}
              disabled={!isRunning}
            >
              Stop
            </button>
            <button type="button" className="ghostButton" onClick={resetLiveState} disabled={disabled}>
              Reset
            </button>
          </div>

          <div className="liveReadout">
            <InfoRow label="Probability" value={`${liveResult?.fall_probability_percent ?? 0}%`} />
            <InfoRow label="Raw" value={`${liveResult?.raw_fall_probability_percent ?? 0}%`} />
            <InfoRow label="Frames" value={`${liveResult?.frames_collected ?? 0}/${liveResult?.frames_required ?? 30}`} />
            <InfoRow label="Votes" value={`${liveResult?.fall_votes ?? 0}/${liveResult?.smoothing_window ?? 0}`} />
            <InfoRow label="Missing" value={liveResult?.missing_frames ?? 0} />
            <InfoRow label="Pose score" value={pose.pose_score ?? "—"} />
            <InfoRow label="Keypoints" value={pose.visible_keypoints ?? "—"} />
          </div>

          {cameraError && <div className="errorBox compactError">{cameraError}</div>}
        </div>
      </div>
    </section>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="infoRow">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default LiveCamera;
