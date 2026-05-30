import os

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from app.config import (
    FALL_PROBABILITY_THRESHOLD,
    HIDDEN_SIZE,
    INPUT_SIZE,
    LSTM_MODEL_PATH,
    NUM_CLASSES,
    SEQ_LEN,
    WARNING_PROBABILITY_THRESHOLD,
    YOLO_CONFIDENCE,
    YOLO_MODEL_NAME,
)
from app.models.lstm_model import FallDetectionLSTM
from app.services.device import get_device
from app.services.fall_decision import SUSTAINED_FALL_WINDOW_THRESHOLD
from app.services.live_smoothing import LiveFallSmoother
from app.services.pose_quality import select_best_person_keypoints
from app.services.preprocessing import normalize_sequence


device = get_device()


class FallDetector:
    def __init__(self):
        print(f"Using device: {device}")

        print("Loading YOLOv8 Pose model...")
        self.yolo_model = YOLO(YOLO_MODEL_NAME)

        print("Loading LSTM model...")
        self.lstm_model = FallDetectionLSTM(
            input_size=INPUT_SIZE,
            hidden_size=HIDDEN_SIZE,
            num_classes=NUM_CLASSES,
        ).to(device)

        if not os.path.exists(LSTM_MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found: {LSTM_MODEL_PATH}. "
                f"Train the model first and put {LSTM_MODEL_PATH} into backend/."
            )

        state_dict = torch.load(LSTM_MODEL_PATH, map_location=device)
        self.lstm_model.load_state_dict(state_dict)
        self.lstm_model.eval()

        self.live_state = LiveFallSmoother()

        print("FallDetector is ready.")

    def get_best_person_keypoints(self, yolo_result):
        keypoints, _ = select_best_person_keypoints(yolo_result)
        return keypoints

    def extract_pose_features(self, frame, previous_center=None):
        results = self.yolo_model(frame, verbose=False, conf=YOLO_CONFIDENCE)

        if len(results) == 0:
            return None, {"person_detected": False, "reason": "no_yolo_result"}

        keypoints, pose_info = select_best_person_keypoints(
            results[0],
            previous_center=previous_center,
            frame_shape=frame.shape,
        )

        if keypoints is None:
            return None, pose_info

        frame_features = keypoints.flatten()

        if len(frame_features) != INPUT_SIZE:
            pose_info["reason"] = "invalid_feature_size"
            return None, pose_info

        return frame_features.astype(np.float32), pose_info

    def extract_frame_features(self, frame):
        frame_features, _ = self.extract_pose_features(frame)

        if frame_features is None:
            return np.zeros(INPUT_SIZE, dtype=np.float32)

        return frame_features

    def predict_sequence(self, sequence):
        normalized_sequence = normalize_sequence(sequence)

        input_data = np.array([normalized_sequence], dtype=np.float32)
        input_tensor = torch.tensor(input_data).to(device)

        with torch.no_grad():
            outputs = self.lstm_model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            fall_probability = probabilities[0, 1].item()

        return fall_probability

    def predict_video(self, video_path):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise RuntimeError("Could not open video file.")

        sequence_buffer = []
        fall_probabilities = []
        frame_count = 0
        reliable_pose_frames = 0
        previous_center = None

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            frame_features, pose_info = self.extract_pose_features(
                frame,
                previous_center=previous_center,
            )

            if frame_features is None:
                continue

            center = pose_info.get("center")
            if center and len(center) == 2:
                previous_center = (float(center[0]), float(center[1]))

            reliable_pose_frames += 1
            sequence_buffer.append(frame_features)

            if len(sequence_buffer) > SEQ_LEN:
                sequence_buffer.pop(0)

            if len(sequence_buffer) == SEQ_LEN:
                sequence = np.array(sequence_buffer, dtype=np.float32)
                fall_probability = self.predict_sequence(sequence)
                fall_probabilities.append(fall_probability)

        cap.release()

        if frame_count == 0:
            raise RuntimeError("Video contains no readable frames.")

        if len(fall_probabilities) == 0:
            max_probability = 0.0
            mean_probability = 0.0
            fall_window_count = 0
            fall_window_ratio = 0.0
            peak_fall_streak = 0
        else:
            max_probability = float(np.max(fall_probabilities))
            mean_probability = float(np.mean(fall_probabilities))
            fall_window_flags = [
                probability >= SUSTAINED_FALL_WINDOW_THRESHOLD
                for probability in fall_probabilities
            ]
            fall_window_count = sum(fall_window_flags)
            fall_window_ratio = fall_window_count / len(fall_probabilities)
            peak_fall_streak = 0
            current_fall_streak = 0

            for is_fall_window in fall_window_flags:
                if is_fall_window:
                    current_fall_streak += 1
                    peak_fall_streak = max(peak_fall_streak, current_fall_streak)
                else:
                    current_fall_streak = 0

        if reliable_pose_frames == 0:
            status = "no_person"
            label = "NO PERSON"
            message = "No reliable person pose detected in video"
            is_fall = False
            risk_level = "low"
        elif len(fall_probabilities) == 0:
            status = "safe"
            label = "SAFE"
            message = "Not enough reliable pose frames for fall sequence"
            is_fall = False
            risk_level = "low"
        elif max_probability >= FALL_PROBABILITY_THRESHOLD:
            status = "fall"
            label = "FALL DETECTED"
            message = "Fall detected"
            is_fall = True
            risk_level = "high"
        elif max_probability >= WARNING_PROBABILITY_THRESHOLD:
            status = "warning"
            label = "WARNING"
            message = "Possible fall risk"
            is_fall = False
            risk_level = "medium"
        else:
            status = "safe"
            label = "SAFE"
            message = "No fall detected"
            is_fall = False
            risk_level = "low"

        return {
            "status": status,
            "is_fall": is_fall,
            "risk_level": risk_level,
            "fall_probability": max_probability,
            "fall_probability_percent": round(max_probability * 100, 2),
            "mean_fall_probability": mean_probability,
            "mean_fall_probability_percent": round(mean_probability * 100, 2),
            "fall_window_count": int(fall_window_count),
            "fall_window_ratio": round(fall_window_ratio, 4),
            "peak_fall_streak": int(peak_fall_streak),
            "label": label,
            "message": message,
            "frames_processed": frame_count,
            "reliable_pose_frames": reliable_pose_frames,
            "windows_analyzed": len(fall_probabilities),
        }

    def reset_live_state(self):
        self.live_state.reset()

    def predict_frame(self, frame):
        frame_features, pose_info = self.extract_pose_features(
            frame,
            previous_center=self.live_state.last_center,
        )

        if frame_features is None:
            return self.live_state.mark_missing(pose_info)

        return self.live_state.add_pose(
            frame_features,
            pose_info,
            self.predict_sequence,
        )
