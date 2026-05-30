from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from ultralytics import YOLO


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import (  # noqa: E402
    HIDDEN_SIZE,
    INPUT_SIZE,
    LSTM_MODEL_PATH,
    NUM_CLASSES,
    SEQ_LEN,
    YOLO_CONFIDENCE,
    YOLO_MODEL_NAME,
)
from app.models.lstm_model import FallDetectionLSTM  # noqa: E402
from app.services.device import get_device  # noqa: E402
from app.services.live_smoothing import LiveFallSmoother  # noqa: E402
from app.services.pose_quality import select_best_person_keypoints  # noqa: E402
from app.services.preprocessing import normalize_sequence  # noqa: E402


CAMERA_ID = 0

STATUS_COLORS = {
    "fall": (0, 0, 255),
    "warning": (0, 165, 255),
    "safe": (0, 255, 0),
    "collecting": (255, 255, 0),
    "no_person": (0, 255, 255),
}

device = get_device()
print(f"Inference device: {device}")


def load_lstm_model():
    model = FallDetectionLSTM(
        input_size=INPUT_SIZE,
        hidden_size=HIDDEN_SIZE,
        num_classes=NUM_CLASSES,
    ).to(device)

    try:
        state_dict = torch.load(LSTM_MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        print("LSTM weights loaded.")
    except FileNotFoundError:
        print(f"Model file not found: {LSTM_MODEL_PATH}")
        print("Run train_lstm.py first, then put the model file into backend/.")
        raise SystemExit(1)
    except Exception as exc:
        print(f"Could not load LSTM model: {exc}")
        raise SystemExit(1)

    model.eval()
    return model


def predict_sequence(model, sequence):
    normalized_sequence = normalize_sequence(sequence)
    input_data = np.array([normalized_sequence], dtype=np.float32)
    input_tensor = torch.tensor(input_data).to(device)

    with torch.no_grad():
        outputs = model(input_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        return probabilities[0, 1].item()


def draw_overlay(
    frame,
    status,
    label,
    raw_probability,
    smoothed_probability,
    fall_votes,
    sequence_size,
    history_size,
    missing_frames,
    pose_info,
):
    color = STATUS_COLORS.get(status, (255, 255, 255))

    cv2.putText(
        frame,
        label,
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        3,
    )

    cv2.putText(
        frame,
        f"Fall probability: {smoothed_probability:.2f} smoothed | {raw_probability:.2f} raw",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (255, 255, 255),
        2,
    )

    cv2.putText(
        frame,
        (
            f"Buffer: {sequence_size}/{SEQ_LEN} | "
            f"votes: {fall_votes}/{history_size} | "
            f"missing: {missing_frames}"
        ),
        (20, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.66,
        (255, 255, 255),
        2,
    )

    if pose_info:
        pose_text = (
            f"Pose score: {pose_info.get('pose_score', 0)} | "
            f"visible keypoints: {pose_info.get('visible_keypoints', 0)}"
        )
        cv2.putText(
            frame,
            pose_text,
            (20, 158),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.66,
            (255, 255, 255),
            2,
        )


def main():
    yolo_model = YOLO(YOLO_MODEL_NAME)
    lstm_model = load_lstm_model()
    live_state = LiveFallSmoother()

    cap = cv2.VideoCapture(CAMERA_ID)

    if not cap.isOpened():
        print("Could not open camera.")
        return

    print("\nLive demo started.")
    print("Press 'q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        yolo_results = yolo_model(frame, verbose=False, conf=YOLO_CONFIDENCE)
        display_frame = yolo_results[0].plot() if len(yolo_results) > 0 else frame

        frame_features = None
        pose_info = {}

        if len(yolo_results) > 0:
            keypoints, pose_info = select_best_person_keypoints(
                yolo_results[0],
                previous_center=live_state.last_center,
                frame_shape=frame.shape,
            )

            if keypoints is not None:
                candidate_features = keypoints.flatten()

                if len(candidate_features) == INPUT_SIZE:
                    frame_features = candidate_features.astype(np.float32)

        if frame_features is None:
            result = live_state.mark_missing(pose_info)
        else:
            result = live_state.add_pose(
                frame_features,
                pose_info,
                lambda sequence: predict_sequence(lstm_model, sequence),
            )

        draw_overlay(
            display_frame,
            result["status"],
            result["label"],
            result["raw_fall_probability"],
            result["fall_probability"],
            result["fall_votes"],
            result["frames_collected"],
            result["smoothing_window"],
            result["missing_frames"],
            result.get("pose", {}),
        )

        cv2.imshow("ElderGuard Live Fall Detection", display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
