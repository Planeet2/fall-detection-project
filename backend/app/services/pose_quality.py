from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from app.config import (
    POSE_KEYPOINT_CONFIDENCE,
    POSE_MIN_MEAN_CONFIDENCE,
    POSE_MIN_TORSO_CONFIDENCE,
    POSE_MIN_VISIBLE_KEYPOINTS,
)


TORSO_KEYPOINTS = (5, 6, 11, 12)


@dataclass
class PoseCandidate:
    index: int
    keypoints: np.ndarray
    center: Optional[tuple[float, float]]
    visible_keypoints: int
    mean_confidence: float
    torso_confidence: float
    bbox_area_ratio: float
    score: float

    def metadata(self) -> dict[str, Any]:
        center = None
        if self.center is not None:
            center = [round(self.center[0], 2), round(self.center[1], 2)]

        return {
            "person_index": self.index,
            "person_detected": True,
            "center": center,
            "visible_keypoints": self.visible_keypoints,
            "mean_confidence": round(self.mean_confidence, 3),
            "torso_confidence": round(self.torso_confidence, 3),
            "bbox_area_ratio": round(self.bbox_area_ratio, 4),
            "pose_score": round(self.score, 3),
        }


def _to_numpy(value):
    if value is None:
        return None

    if hasattr(value, "cpu"):
        value = value.cpu()

    if hasattr(value, "numpy"):
        return value.numpy()

    return np.asarray(value)


def _frame_area(frame_shape) -> float:
    if not frame_shape or len(frame_shape) < 2:
        return 0.0

    height, width = frame_shape[:2]
    return float(max(height, 1) * max(width, 1))


def _get_boxes(yolo_result):
    boxes = getattr(yolo_result, "boxes", None)

    if boxes is None or getattr(boxes, "xyxy", None) is None:
        return None

    return _to_numpy(boxes.xyxy)


def _bbox_area_ratio(boxes, index: int, frame_shape) -> float:
    if boxes is None or index >= len(boxes):
        return 0.0

    frame_area = _frame_area(frame_shape)

    if frame_area <= 0:
        return 0.0

    x1, y1, x2, y2 = boxes[index][:4]
    width = max(float(x2 - x1), 0.0)
    height = max(float(y2 - y1), 0.0)

    return min((width * height) / frame_area, 1.0)


def _visible_center(keypoints: np.ndarray) -> Optional[tuple[float, float]]:
    confidences = keypoints[:, 2]
    torso_mask = confidences[list(TORSO_KEYPOINTS)] >= POSE_KEYPOINT_CONFIDENCE
    torso_points = keypoints[list(TORSO_KEYPOINTS), :2][torso_mask]

    if len(torso_points) >= 2:
        center = torso_points.mean(axis=0)
        return float(center[0]), float(center[1])

    visible_points = keypoints[confidences >= POSE_KEYPOINT_CONFIDENCE, :2]

    if len(visible_points) == 0:
        return None

    center = visible_points.mean(axis=0)
    return float(center[0]), float(center[1])


def _continuity_score(center, previous_center, frame_shape) -> float:
    if center is None or previous_center is None:
        return 0.0

    frame_area = _frame_area(frame_shape)

    if frame_area <= 0:
        return 0.0

    height, width = frame_shape[:2]
    diagonal = max(float(np.hypot(width, height)), 1.0)
    distance = float(np.hypot(center[0] - previous_center[0], center[1] - previous_center[1]))

    return max(0.0, 1.0 - distance / (diagonal * 0.35))


def select_best_person_keypoints(yolo_result, previous_center=None, frame_shape=None):
    if yolo_result.keypoints is None or yolo_result.keypoints.data is None:
        return None, {"person_detected": False, "reason": "no_keypoints"}

    keypoints_data = _to_numpy(yolo_result.keypoints.data)

    if keypoints_data is None or len(keypoints_data) == 0:
        return None, {"person_detected": False, "reason": "no_people"}

    boxes = _get_boxes(yolo_result)
    candidates = []

    for index, keypoints in enumerate(keypoints_data):
        if keypoints.shape != (17, 3):
            continue

        confidences = keypoints[:, 2]
        visible_keypoints = int(np.sum(confidences >= POSE_KEYPOINT_CONFIDENCE))
        mean_confidence = float(np.mean(confidences))
        torso_confidence = float(np.mean(confidences[list(TORSO_KEYPOINTS)]))

        if visible_keypoints < POSE_MIN_VISIBLE_KEYPOINTS:
            continue

        if mean_confidence < POSE_MIN_MEAN_CONFIDENCE:
            continue

        if torso_confidence < POSE_MIN_TORSO_CONFIDENCE:
            continue

        center = _visible_center(keypoints)
        area_ratio = _bbox_area_ratio(boxes, index, frame_shape)
        area_score = min(area_ratio * 12.0, 1.0)
        continuity = _continuity_score(center, previous_center, frame_shape)
        visible_score = min(visible_keypoints / 17.0, 1.0)

        score = (
            mean_confidence * 0.38
            + torso_confidence * 0.32
            + visible_score * 0.15
            + area_score * 0.10
            + continuity * 0.05
        )

        candidates.append(
            PoseCandidate(
                index=index,
                keypoints=keypoints.astype(np.float32),
                center=center,
                visible_keypoints=visible_keypoints,
                mean_confidence=mean_confidence,
                torso_confidence=torso_confidence,
                bbox_area_ratio=area_ratio,
                score=score,
            )
        )

    if not candidates:
        return None, {
            "person_detected": False,
            "reason": "low_pose_quality",
            "candidates_seen": int(len(keypoints_data)),
        }

    best_candidate = max(candidates, key=lambda item: item.score)
    return best_candidate.keypoints, best_candidate.metadata()
