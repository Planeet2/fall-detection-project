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

SMOOTHING_WINDOW = 15
FALL_THRESHOLD = 0.6

CAMERA_ID = 0


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")

    if torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


device = get_device()
print(f"Инференс на устройстве: {device}")


def normalize_sequence(seq):
    """
    Нормализует последовательность keypoints перед подачей в LSTM.

    Вход:
        seq shape: (SEQ_LEN, 51)
    """
    seq = np.asarray(seq, dtype=np.float32).copy()

    if seq.ndim != 2 or seq.shape[1] != INPUT_SIZE:
        raise ValueError(f"Ожидался размер sequence: (frames, {INPUT_SIZE}), получено: {seq.shape}")

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


def get_best_person_keypoints(yolo_result):
    """
    Если в кадре несколько людей, выбираем человека
    с максимальной средней уверенностью keypoints.
    """
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


def load_lstm_model():
    model = FallDetectionLSTM(
        input_size=INPUT_SIZE,
        hidden_size=HIDDEN_SIZE,
        num_classes=NUM_CLASSES
    ).to(device)

    try:
        state_dict = torch.load(LSTM_MODEL_PATH, map_location=device)
        model.load_state_dict(state_dict)
        print("Веса LSTM успешно подключены!")
    except FileNotFoundError:
        print(f"Ошибка: файл модели не найден: {LSTM_MODEL_PATH}")
        print("Сначала запустите train_lstm.py для обучения модели.")
        exit()
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}")
        exit()

    model.eval()
    return model


def main():
    yolo_model = YOLO(YOLO_MODEL_NAME)
    lstm_model = load_lstm_model()

    sequence_buffer = []
    prediction_history = []
    probability_history = []

    cap = cv2.VideoCapture(CAMERA_ID)

    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру.")
        return

    print("\nИИ-демо запущено.")
    print("Нажмите 'q', чтобы выйти.")

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        yolo_results = yolo_model(frame, verbose=False)

        current_prediction = 0
        fall_probability = 0.0

        if len(yolo_results) > 0:
            yolo_output = yolo_results[0]

            if yolo_output.keypoints is not None and len(yolo_output.keypoints.data) > 0:
                frame = yolo_output.plot()

                keypoints = get_best_person_keypoints(yolo_output)

                if keypoints is not None:
                    frame_features = keypoints.flatten()

                    if len(frame_features) == INPUT_SIZE:
                        sequence_buffer.append(frame_features)
                    else:
                        sequence_buffer.append([0.0] * INPUT_SIZE)
                else:
                    sequence_buffer.append([0.0] * INPUT_SIZE)
            else:
                
                if len(sequence_buffer) > 0:
                    sequence_buffer.append([0.0] * INPUT_SIZE)
        else:
            if len(sequence_buffer) > 0:
                sequence_buffer.append([0.0] * INPUT_SIZE)

        if len(sequence_buffer) > SEQ_LEN:
            sequence_buffer.pop(0)

        if len(sequence_buffer) == SEQ_LEN:
            raw_sequence = np.array(sequence_buffer, dtype=np.float32)
            normalized_sequence = normalize_sequence(raw_sequence)

            input_data = np.array([normalized_sequence], dtype=np.float32)
            input_tensor = torch.tensor(input_data).to(device)

            with torch.no_grad():
                outputs = lstm_model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)

                fall_probability = probabilities[0, 1].item()
                current_prediction = 1 if fall_probability >= 0.5 else 0

        prediction_history.append(current_prediction)
        probability_history.append(fall_probability)

        if len(prediction_history) > SMOOTHING_WINDOW:
            prediction_history.pop(0)

        if len(probability_history) > SMOOTHING_WINDOW:
            probability_history.pop(0)

        # Сглаживание
        if len(prediction_history) == SMOOTHING_WINDOW:
            smoothed_prediction = np.mean(prediction_history)
            smoothed_probability = np.mean(probability_history)
        else:
            smoothed_prediction = 0.0
            smoothed_probability = 0.0

        if smoothed_prediction > FALL_THRESHOLD:
            status_text = "CRITICAL: FALL DETECTED!"
            text_color = (0, 0, 255)
        else:
            status_text = "STATUS: SAFE (NORMAL)"
            text_color = (0, 255, 0)

        probability_text = f"Fall probability: {smoothed_probability:.2f}"

        cv2.putText(
            frame,
            status_text,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            text_color,
            3
        )

        cv2.putText(
            frame,
            probability_text,
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Buffer: {len(sequence_buffer)}/{SEQ_LEN}",
            (20, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow("Elderly Fall Detection - YOLOv8 Pose + LSTM", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()