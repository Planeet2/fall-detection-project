from collections import deque
from typing import Callable

import numpy as np

from app.config import (
    FALL_PROBABILITY_THRESHOLD,
    LIVE_FALL_CONFIRM_FRAMES,
    LIVE_MISSING_RESET_FRAMES,
    LIVE_SMOOTHING_WINDOW,
    SEQ_LEN,
    WARNING_PROBABILITY_THRESHOLD,
)


class LiveFallSmoother:
    def __init__(
        self,
        seq_len: int = SEQ_LEN,
        smoothing_window: int = LIVE_SMOOTHING_WINDOW,
        fall_confirm_frames: int = LIVE_FALL_CONFIRM_FRAMES,
        missing_reset_frames: int = LIVE_MISSING_RESET_FRAMES,
    ):
        self.seq_len = max(seq_len, 1)
        self.smoothing_window = max(smoothing_window, 1)
        self.fall_confirm_frames = min(
            max(fall_confirm_frames, 1),
            self.smoothing_window,
        )
        self.missing_reset_frames = max(missing_reset_frames, 1)
        self.sequence_buffer = deque(maxlen=self.seq_len)
        self.probability_history = deque(maxlen=self.smoothing_window)
        self.missing_frames = 0
        self.last_center = None

    def reset(self):
        self.sequence_buffer.clear()
        self.probability_history.clear()
        self.missing_frames = 0
        self.last_center = None

    def mark_missing(self, pose_info=None):
        self.missing_frames += 1
        sequence_reset = False

        if self.missing_frames >= self.missing_reset_frames:
            self.sequence_buffer.clear()
            self.probability_history.clear()
            self.last_center = None
            sequence_reset = True

        message = "No reliable person pose detected."
        if sequence_reset:
            message = "No reliable person pose detected. Live sequence was reset."

        return {
            "status": "no_person",
            "is_fall": False,
            "risk_level": "low",
            "fall_probability": 0.0,
            "fall_probability_percent": 0.0,
            "raw_fall_probability": 0.0,
            "raw_fall_probability_percent": 0.0,
            "label": "NO PERSON",
            "message": message,
            "frames_collected": len(self.sequence_buffer),
            "frames_required": self.seq_len,
            "smoothing_window": len(self.probability_history),
            "fall_votes": 0,
            "missing_frames": self.missing_frames,
            "sequence_reset": sequence_reset,
            "person_detected": False,
            "pose": pose_info or {},
        }

    def add_pose(
        self,
        frame_features: np.ndarray,
        pose_info: dict,
        predict_sequence: Callable[[np.ndarray], float],
    ):
        self.missing_frames = 0
        self._update_last_center(pose_info)
        self.sequence_buffer.append(frame_features)

        if len(self.sequence_buffer) < self.seq_len:
            return {
                "status": "collecting",
                "is_fall": False,
                "risk_level": "low",
                "fall_probability": 0.0,
                "fall_probability_percent": 0.0,
                "raw_fall_probability": 0.0,
                "raw_fall_probability_percent": 0.0,
                "label": "COLLECTING",
                "message": "Collecting reliable person poses for live detection",
                "frames_collected": len(self.sequence_buffer),
                "frames_required": self.seq_len,
                "smoothing_window": len(self.probability_history),
                "fall_votes": 0,
                "missing_frames": 0,
                "person_detected": True,
                "pose": pose_info,
            }

        sequence = np.array(self.sequence_buffer, dtype=np.float32)
        raw_probability = float(predict_sequence(sequence))
        self.probability_history.append(raw_probability)

        smoothed_probability = float(np.mean(self.probability_history))
        fall_votes = sum(
            probability >= FALL_PROBABILITY_THRESHOLD
            for probability in self.probability_history
        )

        status, label, message, is_fall, risk_level = self._classify(
            raw_probability,
            smoothed_probability,
            fall_votes,
        )

        return {
            "status": status,
            "is_fall": is_fall,
            "risk_level": risk_level,
            "fall_probability": smoothed_probability,
            "fall_probability_percent": round(smoothed_probability * 100, 2),
            "raw_fall_probability": raw_probability,
            "raw_fall_probability_percent": round(raw_probability * 100, 2),
            "label": label,
            "message": message,
            "frames_collected": len(self.sequence_buffer),
            "frames_required": self.seq_len,
            "smoothing_window": len(self.probability_history),
            "fall_votes": int(fall_votes),
            "missing_frames": 0,
            "person_detected": True,
            "pose": pose_info,
        }

    def _classify(self, raw_probability, smoothed_probability, fall_votes):
        confirmation_ready = len(self.probability_history) >= min(
            self.fall_confirm_frames,
            self.smoothing_window,
        )

        fall_confirmed = (
            confirmation_ready
            and smoothed_probability >= FALL_PROBABILITY_THRESHOLD
            and fall_votes >= self.fall_confirm_frames
        )

        if fall_confirmed:
            return (
                "fall",
                "FALL DETECTED",
                "Fall detected across several reliable live frames",
                True,
                "high",
            )

        if (
            smoothed_probability >= WARNING_PROBABILITY_THRESHOLD
            or raw_probability >= FALL_PROBABILITY_THRESHOLD
        ):
            return (
                "warning",
                "WARNING",
                "Possible fall movement. Waiting for more live-frame confirmation",
                False,
                "medium",
            )

        return (
            "safe",
            "SAFE",
            "No fall detected",
            False,
            "low",
        )

    def _update_last_center(self, pose_info):
        center = pose_info.get("center")

        if not center or len(center) != 2:
            return

        self.last_center = (float(center[0]), float(center[1]))
