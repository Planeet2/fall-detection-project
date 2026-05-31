# ElderGuard Agent

## 基于元景万悟的银发守护智能体原型系统  
## Elderly Care Intelligent Agent Prototype Based on Yuanjing Wanwu

ElderGuard Agent is an intelligent elderly care prototype designed for home monitoring and emergency response.  
The system combines computer vision, fall detection, backend API services, frontend dashboard, and an agent workflow design based on Yuanjing Wanwu / 元景万悟.

The project is developed for the AI track topic:

**基于大模型技术的银发守护智能体应用开发**  
**Development of an elderly care intelligent agent based on large model technology**

---

## 1. Project Background

Many elderly people live alone and face safety risks such as falling, unstable walking, long periods of inactivity, and sudden health problems. Traditional monitoring methods often rely on manual observation or wearable devices, which may be inconvenient for elderly users.

This project provides a prototype of an intelligent elderly care agent that can:

- analyze uploaded video;
- detect possible falls;
- estimate fall probability;
- classify risk level;
- generate agent decisions;
- simulate emergency workflow;
- provide daily care reminders;
- protect user privacy.

---

## 2. Main Features

### 2.1 Video-based Fall Detection

The backend analyzes uploaded video and detects whether a fall occurred.

The system returns:

- detection status;
- fall probability;
- risk level;
- frames processed;
- windows analyzed;
- detection ID;
- timestamp.

### 2.2 ElderGuard Agent Decision

After the backend generates a structured behavior event, the local agent logic simulates how Yuanjing Wanwu would make decisions.

For example:

- low risk → save event log;
- medium risk → ask elder for confirmation;
- high risk → trigger emergency workflow.

### 2.3 Emergency Workflow

When a high-risk fall is detected, the system can simulate:

- voice confirmation request;
- family notification;
- incident report generation;
- event log saving.

### 2.4 Daily Care Module

The frontend includes a care module for elderly users:

- medicine reminder;
- weather reminder;
- health suggestion;
- emotional care scenario.

### 2.5 Privacy Protection

The system design follows privacy protection principles:

- raw video is processed locally;
- the agent receives only structured behavior events;
- sensitive actions require confirmation;
- privacy protection is shown in the dashboard.

---

## 3. Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- OpenCV
- PyTorch
- Ultralytics YOLOv8 Pose
- LSTM model

### Frontend

- React
- Vite
- JavaScript
- CSS

### AI / Agent Design

- YOLOv8 Pose for body keypoint extraction
- LSTM for movement sequence classification
- Yuanjing Wanwu agent design
- Knowledge base
- Workflow
- MCP / HTTP tool integration concept

---

## 4. System Architecture

```text
Camera / Uploaded Video
        ↓
Frontend Dashboard
        ↓
FastAPI Backend
        ↓
YOLOv8 Pose
        ↓
LSTM Fall Detection Model
        ↓
Structured Behavior Event
        ↓
ElderGuard Agent Decision Layer
        ↓
Emergency Workflow / Daily Care / Event Log
```

---

## 5. Yuanjing Wanwu Agent Design

The project includes a `yuanjing_agent/` folder that describes how the system can be connected to Yuanjing Wanwu.

```text
yuanjing_agent/
├── knowledge_base/
│   ├── elder_profile.md
│   ├── fall_response_rules.md
│   ├── daily_care_rules.md
│   └── emergency_contacts.md
├── prompts/
│   └── elderguard_agent_prompt.md
└── workflow/
    └── elderguard_workflow.md
```

### 5.1 Knowledge Base

The knowledge base stores:

- elder profile;
- fall response rules;
- daily care rules;
- emergency contacts;
- privacy rules.

### 5.2 Agent Prompt

The agent prompt defines the role of ElderGuard Agent:

- analyze behavior events;
- classify risk;
- generate messages;
- prepare emergency response;
- generate incident reports;
- follow privacy rules.

### 5.3 Workflow

The workflow describes the emergency decision process:

```text
Receive behavior event
        ↓
Classify risk
        ↓
Low risk / Medium risk / High risk branch
        ↓
Generate message
        ↓
Notify family if needed
        ↓
Save event log
```

---

## 6. Backend API

### Health Check

```http
GET /health
```

### Readiness Check

```http
GET /ready
```

This endpoint checks whether the model files and PostgreSQL storage are ready.

### Model Info

```http
GET /model-info
```

### Predict Video

```http
POST /predict-video
```

Input:

- video file: `.mp4`, `.mov`, `.avi`, `.webm`

Confirmed fall output example:

```json
{
  "status": "fall",
  "is_fall": true,
  "confirmed_fall": true,
  "needs_manual_review": false,
  "decision_reason": "High fall probability, sufficient pose reliability, sufficient mean probability, and sustained fall window ratio",
  "pose_reliability_ratio": 0.98,
  "risk_level": "high",
  "fall_probability": 0.9997,
  "fall_probability_percent": 99.97,
  "label": "FALL DETECTED",
  "message": "Fall detected",
  "frames_processed": 156,
  "windows_analyzed": 127,
  "agent": {
    "decision": "emergency_workflow",
    "decision_label": "Emergency workflow started",
    "elder_message": "A possible fall was detected. Are you okay?",
    "family_message": "Possible fall detected. Please check immediately.",
    "next_action": "wait_for_elder_confirmation"
  },
  "agent_result": {
    "risk_level": "high",
    "notify_caregiver": true,
    "message": "A fall was detected. Please check immediately.",
    "recommendation": "Contact the elder and verify their condition.",
    "reason": "The fall detector reported a high-confidence fall event."
  }
}
```

Suspicious output example:

```json
{
  "status": "suspicious",
  "is_fall": false,
  "confirmed_fall": false,
  "needs_manual_review": true,
  "decision_reason": "High peak fall probability but insufficient sustained fall evidence",
  "pose_reliability_ratio": 0.98,
  "fall_probability_percent": 99.95,
  "label": "POSSIBLE FALL - REVIEW NEEDED",
  "agent": {
    "decision": "manual_review",
    "decision_label": "Manual review required",
    "next_action": "review_video"
  },
  "agent_result": null
}
```

Normal output example:

```json
{
  "status": "normal",
  "is_fall": false,
  "confirmed_fall": false,
  "needs_manual_review": false,
  "decision_reason": "Fall probability below suspicious threshold",
  "pose_reliability_ratio": 0.94,
  "fall_probability_percent": 12.4,
  "agent_result": null
}
```

The backend now applies a post-processing decision layer after the YOLO Pose + LSTM prediction:

- `normal`: fall probability is below the suspicious threshold;
- `suspicious`: movement may look like a fall, but the video quality, mean probability, or sustained evidence is not enough for emergency workflow;
- `fall`: confirmed fall with high peak probability, sufficient mean probability, sufficient pose reliability, enough analyzed windows, and sustained fall window ratio.

High peak `fall_probability` alone is not enough to confirm a fall. A confirmed fall also requires `fall_window_ratio >= 0.25`, `mean_fall_probability >= 0.50`, and reliable pose tracking. If the peak is high but sustained evidence is weak, the response is `suspicious` and the emergency workflow is not started.

This reduces false positives from ordinary actions such as sitting, bending, lying down, poor camera angles, or partial body tracking loss.

Yuanjing-compatible agent analysis is called only when `confirmed_fall` is `true`.
For `suspicious`, `normal`, no-person, and live-frame responses, `agent_result` is `null` and no Yuanjing request is made.
If `YUANJING_API_KEY` is missing or the agent call fails, fall detection still succeeds and `agent_result` contains a safe fallback explanation.

### Detection History

```http
GET /detections
```

### Statistics

```http
GET /stats
```

### Mock Notification

```http
POST /mock-notify
```

This endpoint simulates family notification for the demo version.

### Yuanjing Agent Test

```http
POST /agent/test
```

Example payload:

```json
{
  "elder_name": "Ivan",
  "age": 78,
  "event": "fall_detected",
  "confidence": 0.91,
  "location": "bedroom",
  "has_chronic_disease": true
}
```

If `YUANJING_API_KEY` is not configured, this endpoint returns a safe fallback response instead of failing.

Yuanjing-compatible settings are read from `backend/.env`:

```env
YUANJING_API_KEY=
YUANJING_BASE_URL=https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1
YUANJING_MODEL=deepseek-v3
```

---

## 7. How to Run

### 7.1 Backend

Go to the backend folder:

```bash
cd backend
```

Install dependencies:

```bash
pip install -r ../requirements.txt
```

Run backend:

```bash
uvicorn app.main:app --reload
```

Backend will run at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

### 7.2 Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm run dev
```

Frontend will run at:

```text
http://localhost:3000
```

---

## 8. Demo Scenario

### Step 1

Open the frontend dashboard.

### Step 2

Upload a test video.

### Step 3

Click:

```text
Analyze Video
```

### Step 4

The backend analyzes the video and returns:

- fall status;
- probability;
- risk level;
- model details.

### Step 5

The agent layer generates a decision:

```text
Manual review required / Emergency workflow started
```

### Step 6

The dashboard shows:

- message to elder;
- message to family;
- workflow actions;
- mock notification button;
- detection history;
- daily care information.

---

## 9. Current Implementation Status

Implemented:

- frontend dashboard;
- backend video upload API;
- YOLOv8 Pose keypoint extraction;
- LSTM fall detection;
- risk level classification;
- detection history;
- statistics;
- local agent decision logic;
- post-processing fall decision layer with normal, suspicious, and confirmed fall states;
- mock emergency notification;
- Yuanjing Wanwu agent design files;
- Yuanjing-compatible agent call after confirmed fall detection.

Planned:

- production Yuanjing Wanwu workflow registration;
- real MCP / HTTP tool registration;
- real SMS or WeChat notification API;
- voice interaction;
- continuous camera monitoring;
- real elderly profile management;
- multi-user care dashboard.

---

## 10. Project Value

This project demonstrates how a computer vision model can be extended into an intelligent elderly care agent.

The local backend is responsible for video understanding and behavior analysis.  
The Yuanjing Wanwu agent layer is designed to handle decision-making, workflow orchestration, knowledge base reasoning, and emergency response.

The prototype shows a practical path from:

```text
fall detection model
```

to:

```text
elderly care intelligent agent
```

---

## 11. Privacy and Safety

The system avoids exposing raw video to the agent layer.  
Only structured behavior events are sent to the decision module.

Privacy principles:

- local video processing;
- structured event transmission;
- no raw video exposure;
- sensitive actions require confirmation;
- emergency escalation follows rule-based workflow.

---

## 12. Team

Project: ElderGuard Agent  
Scenario: Elderly care and fall detection  
AI track: Yuanjing Wanwu elderly care intelligent agent prototype
