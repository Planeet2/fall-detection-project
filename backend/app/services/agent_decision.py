def build_agent_decision(result):
    status = result.get("status", "safe")
    risk_level = result.get("risk_level", "low")
    probability = result.get("fall_probability_percent") or 0

    if status == "fall" or risk_level == "high" or probability >= 70:
        return {
            "decision": "emergency_workflow",
            "decision_label": "Emergency workflow started",
            "risk_level": "high",
            "elder_message": (
                "爷爷/奶奶，系统检测到您可能摔倒了。"
                "请问您现在还好吗？如果需要帮助，请说“需要帮助”。"
            ),
            "family_message": (
                f"监测到老人可能发生跌倒，跌倒概率为 {probability}%。"
                "系统已准备进行语音确认，请尽快查看。"
            ),
            "actions": [
                "Voice confirmation requested",
                "Family notification prepared",
                "Incident report generated",
                "Event saved to detection log",
            ],
            "next_action": "wait_for_elder_confirmation",
        }

    if status == "warning" or risk_level == "medium" or probability >= 30:
        return {
            "decision": "warning_check",
            "decision_label": "Warning check started",
            "risk_level": "medium",
            "elder_message": (
                "检测到您的活动状态可能不稳定。"
                "请先坐下休息，并确认您现在是否安全。"
            ),
            "family_message": "",
            "actions": [
                "Gentle voice check requested",
                "Warning event saved to detection log",
                "Continue observation",
            ],
            "next_action": "observe_status",
        }

    return {
        "decision": "normal_care",
        "decision_label": "Normal activity",
        "risk_level": "low",
        "elder_message": "当前活动状态正常。请注意休息，保持安全。",
        "family_message": "",
        "actions": [
            "Event saved to detection log",
            "Daily care suggestion available",
        ],
        "next_action": "no_action_required",
    }
