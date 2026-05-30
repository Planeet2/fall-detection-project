def build_agent_decision(result):
    status = result.get("status", "safe")
    risk_level = result.get("risk_level", "low")
    probability = result.get("fall_probability_percent") or 0
    confirmed_fall = result.get("confirmed_fall") is True
    needs_manual_review = result.get("needs_manual_review") is True

    if status == "no_person":
        return {
            "decision": "tracking_lost",
            "decision_label": "Person pose not reliable",
            "risk_level": "low",
            "elder_message": "当前画面未稳定识别到人体姿态，请保持在摄像头可见范围内。",
            "family_message": "",
            "actions": [
                "Ignore low-quality live frame",
                "Keep searching for reliable person pose",
                "Reset live buffer if tracking is lost for too long",
            ],
            "next_action": "continue_pose_tracking",
        }

    if status == "collecting":
        return {
            "decision": "collect_live_frames",
            "decision_label": "Collecting reliable live frames",
            "risk_level": "low",
            "elder_message": "系统正在稳定识别您的活动状态，请稍等。",
            "family_message": "",
            "actions": [
                "Collect reliable pose frames",
                "Wait for enough movement sequence data",
                "Do not trigger emergency workflow yet",
            ],
            "next_action": "continue_collecting_frames",
        }

    if status == "suspicious" or needs_manual_review:
        return {
            "decision": "manual_review",
            "decision_label": "Manual review required",
            "risk_level": "medium",
            "elder_message": (
                "检测到一个疑似跌倒动作，但系统还没有确认发生跌倒。"
                "请保持安全，必要时请回应需要帮助。"
            ),
            "family_message": "",
            "actions": [
                "Manual review recommended",
                "No emergency workflow started",
                "Continue observation",
            ],
            "next_action": "review_video",
        }

    if confirmed_fall:
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

    if status == "fall" or risk_level == "high" or probability >= 70:
        return {
            "decision": "manual_review",
            "decision_label": "Manual review required",
            "risk_level": "medium",
            "elder_message": (
                "检测到高风险动作，但系统还没有确认发生跌倒。"
                "请确认您现在是否安全。"
            ),
            "family_message": "",
            "actions": [
                "Manual review recommended",
                "No emergency workflow started",
                "Continue observation",
            ],
            "next_action": "review_video",
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
