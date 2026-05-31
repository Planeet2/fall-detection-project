from app.services.agent_decision import build_agent_decision
from app.services.fall_decision import classify_fall_decision


def main():
    decision = classify_fall_decision(
        fall_probability=0.9995064735412598,
        frames_processed=230,
        reliable_pose_frames=227,
        windows_analyzed=198,
        additional_context={
            "mean_fall_probability": 0.3944890244318304,
            "fall_window_ratio": 0.2071,
            "peak_fall_streak": 41,
        },
    )
    agent = build_agent_decision(
        {
            **decision,
            "fall_probability_percent": 99.95,
        }
    )

    assert decision["status"] == "suspicious"
    assert decision["confirmed_fall"] is False
    assert decision["needs_manual_review"] is True
    assert agent["decision"] == "manual_review"

    print("fall_decision_smoke_ok")


if __name__ == "__main__":
    main()
