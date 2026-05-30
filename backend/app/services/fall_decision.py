MIN_FRAMES_PROCESSED = 20
MIN_WINDOWS_ANALYZED = 5
MIN_POSE_RELIABILITY_RATIO = 0.6
SUSPICIOUS_THRESHOLD = 0.50
CONFIRMED_FALL_THRESHOLD = 0.90
SUSTAINED_FALL_WINDOW_THRESHOLD = 0.85
MIN_FALL_WINDOW_RATIO = 0.25
MIN_CONSECUTIVE_FALL_WINDOWS = 3


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def calculate_pose_reliability_ratio(
    frames_processed: int,
    reliable_pose_frames: int,
) -> float:
    if frames_processed <= 0:
        return 0.0

    return round(reliable_pose_frames / frames_processed, 4)


def _decision(
    *,
    status: str,
    is_fall: bool,
    confirmed_fall: bool,
    risk_level: str,
    label: str,
    message: str,
    decision_reason: str,
    needs_manual_review: bool,
    pose_reliability_ratio: float,
) -> dict:
    return {
        "status": status,
        "is_fall": is_fall,
        "confirmed_fall": confirmed_fall,
        "risk_level": risk_level,
        "label": label,
        "message": message,
        "decision_reason": decision_reason,
        "needs_manual_review": needs_manual_review,
        "pose_reliability_ratio": pose_reliability_ratio,
    }


def _normal(reason: str, pose_reliability_ratio: float) -> dict:
    return _decision(
        status="normal",
        is_fall=False,
        confirmed_fall=False,
        risk_level="low",
        label="NORMAL",
        message="No fall detected",
        decision_reason=reason,
        needs_manual_review=False,
        pose_reliability_ratio=pose_reliability_ratio,
    )


def _suspicious(reason: str, pose_reliability_ratio: float) -> dict:
    return _decision(
        status="suspicious",
        is_fall=False,
        confirmed_fall=False,
        risk_level="medium",
        label="POSSIBLE FALL - REVIEW NEEDED",
        message="Suspicious fall-like movement detected. Manual review is recommended.",
        decision_reason=reason,
        needs_manual_review=True,
        pose_reliability_ratio=pose_reliability_ratio,
    )


def _confirmed(reason: str, pose_reliability_ratio: float) -> dict:
    return _decision(
        status="fall",
        is_fall=True,
        confirmed_fall=True,
        risk_level="high",
        label="FALL DETECTED",
        message="Confirmed fall detected",
        decision_reason=reason,
        needs_manual_review=False,
        pose_reliability_ratio=pose_reliability_ratio,
    )


def _has_sustained_fall_evidence(
    windows_analyzed: int,
    additional_context: dict | None,
) -> bool:
    if not additional_context:
        return True

    fall_window_ratio = additional_context.get("fall_window_ratio")
    peak_fall_streak = additional_context.get("peak_fall_streak")

    if fall_window_ratio is None and peak_fall_streak is None:
        return True

    fall_window_ratio = _to_float(fall_window_ratio)
    peak_fall_streak = _to_int(peak_fall_streak)

    if windows_analyzed <= 0:
        return False

    return (
        fall_window_ratio >= MIN_FALL_WINDOW_RATIO
        or peak_fall_streak >= MIN_CONSECUTIVE_FALL_WINDOWS
    )


def classify_fall_decision(
    fall_probability: float,
    frames_processed: int,
    reliable_pose_frames: int,
    windows_analyzed: int,
    additional_context: dict | None = None,
) -> dict:
    fall_probability = _to_float(fall_probability)
    frames_processed = _to_int(frames_processed)
    reliable_pose_frames = _to_int(reliable_pose_frames)
    windows_analyzed = _to_int(windows_analyzed)
    pose_reliability_ratio = calculate_pose_reliability_ratio(
        frames_processed,
        reliable_pose_frames,
    )

    if frames_processed < MIN_FRAMES_PROCESSED:
        return _suspicious(
            "Not enough processed frames for a reliable fall decision",
            pose_reliability_ratio,
        )

    if reliable_pose_frames <= 0:
        return _suspicious(
            "Not enough reliable pose frames",
            pose_reliability_ratio,
        )

    if windows_analyzed < MIN_WINDOWS_ANALYZED:
        return _suspicious(
            "Not enough analyzed windows",
            pose_reliability_ratio,
        )

    if fall_probability < SUSPICIOUS_THRESHOLD:
        return _normal(
            "Fall probability below suspicious threshold",
            pose_reliability_ratio,
        )

    if pose_reliability_ratio < MIN_POSE_RELIABILITY_RATIO:
        return _suspicious(
            "High fall probability but pose reliability is too low",
            pose_reliability_ratio,
        )

    if fall_probability < CONFIRMED_FALL_THRESHOLD:
        return _suspicious(
            "Fall-like movement detected but probability is below confirmed threshold",
            pose_reliability_ratio,
        )

    if not _has_sustained_fall_evidence(windows_analyzed, additional_context):
        return _suspicious(
            "High peak fall probability but not enough sustained fall evidence",
            pose_reliability_ratio,
        )

    return _confirmed(
        "High fall probability, sufficient pose reliability, and sustained fall evidence",
        pose_reliability_ratio,
    )


def add_live_decision_metadata(result: dict) -> None:
    if result.get("confirmed_fall") is not None:
        return

    status = result.get("status")

    if result.get("is_fall") is True:
        result.update(
            {
                "confirmed_fall": True,
                "needs_manual_review": False,
                "decision_reason": "Live smoother confirmed fall across several reliable frames",
                "pose_reliability_ratio": None,
            }
        )
        return

    if status == "warning":
        result.update(
            {
                "confirmed_fall": False,
                "needs_manual_review": True,
                "decision_reason": "Live frame is warning-level and needs more confirmation",
                "pose_reliability_ratio": None,
            }
        )
        return

    result.update(
        {
            "confirmed_fall": False,
            "needs_manual_review": False,
            "decision_reason": "Live frame is not a confirmed fall",
            "pose_reliability_ratio": None,
        }
    )
