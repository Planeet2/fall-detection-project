# ElderGuard Yuanjing Wanwu Workflow

## Workflow Name

ElderGuard Emergency Response Workflow

## Goal

Receive structured behavior events from the local fall detection backend and decide the correct elderly care action.

## Workflow Steps

1. Start

2. Receive behavior event from backend API

Example input:

{
  "elder_id": "elder_001",
  "status": "fall",
  "risk_level": "high",
  "fall_probability_percent": 99.97,
  "message": "Fall detected"
}

3. Risk classification

Branch rules:

- low risk:
  - save event log;
  - return normal care message.

- medium risk:
  - ask elder for confirmation;
  - suggest rest;
  - save warning log.

- high risk:
  - trigger emergency workflow;
  - generate voice confirmation message;
  - prepare family notification;
  - generate incident report;
  - save event log.

4. Call tools

Tools used in prototype:

- behavior_event_api
- mock_notification_tool
- event_log_tool
- knowledge_base_search
- report_generation_node

5. Output decision

Example output:

{
  "decision": "emergency_workflow",
  "risk_level": "high",
  "elder_message": "A possible fall was detected. Are you okay?",
  "family_message": "Possible fall detected. Please check immediately.",
  "workflow_actions": [
    "Voice confirmation requested",
    "Family notification prepared",
    "Incident report generated",
    "Event saved to log"
  ],
  "next_action": "wait_for_elder_confirmation"
}