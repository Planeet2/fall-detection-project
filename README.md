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

Output example:

```json
{
  "status": "fall",
  "is_fall": true,
  "risk_level": "high",
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
  }
}
```

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
Emergency workflow started
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
- mock emergency notification;
- Yuanjing Wanwu agent design files.

Planned:

- real Yuanjing Wanwu platform integration;
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
