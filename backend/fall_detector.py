import os
import cv2
import torch
import torch.nn as nn
import numpy as np
from ultralytics import YOLO


YOLO_MODEL_NAME = "yolov8n-pose.pt"
LSTM_MODEL_PATH = "fall_detection_lstm.pth"

SEQ_LEN = 30
INPUT_SIZE = 51
HIDDEN_SIZE = 64
NUM_CLASSES = 2

FALL_PROBABILITY_THRESHOLD = 0.6

def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")

    if torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


device = get_device()

class FallDetectionLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes):
        super(FallDetectionLSTM, self).__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True,
            num_layers=2
        )

        self.drop = nn.Dropout(0.4)
        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_time_step = lstm_out[:, -1, :]
        out = self.drop(last_time_step)
        out = self.fc(out)
        return out


def normalize_sequence(seq):
    seq = np.asarray(seq, dtype=np.float32).copy()

    if seq.ndim != 2 or seq.shape[1] != INPUT_SIZE:
        raise ValueError(f"Expected sequence shape: (frames, {INPUT_SIZE}), got: {seq.shape}")

    keypoints = seq.reshape(seq.shape[0], 17, 3)

    xy = keypoints[:, :, :2]
    conf = keypoints[:, :, 2:3]

    left_shoulder = xy[:, 5, :]
    right_shoulder = xy[:, 6, :]
    left_hip = xy[:, 11, :]
    right_hip = xy[:, 12, :]

    center = (left_hip + right_hip) / 2.0
    center = center[:, np.newaxis, :]

    shoulder_dist = np.linalg.norm(left_shoulder - right_shoulder, axis=1)
    shoulder_dist = shoulder_dist.reshape(-1, 1, 1)

    shoulder_dist[shoulder_dist < 1e-6] = 1.0

    xy_normalized = (xy - center) / shoulder_dist

    normalized_keypoints = np.concatenate([xy_normalized, conf], axis=2)
    normalized_seq = normalized_keypoints.reshape(seq.shape[0], INPUT_SIZE)

    return normalized_seq.astype(np.float32)


class FallDetector:
    def __init__(self):
        print(f"Using device: {device}")

        print("Loading YOLOv8 Pose model...")
        self.yolo_model = YOLO(YOLO_MODEL_NAME)

        print("Loading LSTM model...")
        self.lstm_model = FallDetectionLSTM(
            input_size=INPUT_SIZE,
            hidden_size=HIDDEN_SIZE,
            num_classes=NUM_CLASSES
        ).to(device)

        if not os.path.exists(LSTM_MODEL_PATH):
            raise FileNotFoundError(
                f"Model file not found: {LSTM_MODEL_PATH}. "
                f"Train the model first and put {LSTM_MODEL_PATH} into backend/."
            )

        state_dict = torch.load(LSTM_MODEL_PATH, map_location=device)
        self.lstm_model.load_state_dict(state_dict)
        self.lstm_model.eval()

        print("FallDetector is ready.")

    def get_best_person_keypoints(self, yolo_result):

        if yolo_result.keypoints is None:
            return None

        if yolo_result.keypoints.data is None:
            return None

        keypoints_data = yolo_result.keypoints.data

        if len(keypoints_data) == 0:
            return None

        keypoints_np = keypoints_data.cpu().numpy()

        confidences = keypoints_np[:, :, 2]
        mean_confidences = confidences.mean(axis=1)

        best_person_idx = int(np.argmax(mean_confidences))

        return keypoints_np[best_person_idx]

    def extract_frame_features(self, frame):

        results = self.yolo_model(frame, verbose=False)

        if len(results) == 0:
            return np.zeros(INPUT_SIZE, dtype=np.float32)

        keypoints = self.get_best_person_keypoints(results[0])

        if keypoints is None:
            return np.zeros(INPUT_SIZE, dtype=np.float32)

        frame_features = keypoints.flatten()

        if len(frame_features) != INPUT_SIZE:
            return np.zeros(INPUT_SIZE, dtype=np.float32)

        return frame_features.astype(np.float32)

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

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            frame_features = self.extract_frame_features(frame)
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
        else:
            max_probability = float(np.max(fall_probabilities))

        if max_probability >= FALL_PROBABILITY_THRESHOLD:
            status = "fall"
            label = "FALL DETECTED"
            message = "Fall detected"
            is_fall = True
            risk_level = "high"
        elif max_probability >= 0.4:
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
            "label": label,
            "message": message,
            "frames_processed": frame_count,
            "windows_analyzed": len(fall_probabilities)
}