import os
import copy
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim

from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

FEATURES_DIR = "./features/"

SEQ_LEN = 30
INPUT_SIZE = 51       
HIDDEN_SIZE = 64
NUM_CLASSES = 2

BATCH_SIZE = 16
EPOCHS = 50
LEARNING_RATE = 0.0005
WEIGHT_DECAY = 0.01

MODEL_SAVE_PATH = "fall_detection_lstm.pth"

RANDOM_STATE = 42

def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")

    if torch.backends.mps.is_available():
        return torch.device("mps")

    return torch.device("cpu")


device = get_device()
print(f"Обучение на устройстве: {device}")


def normalize_sequence(seq):

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


class SkeletonWindowDataset(Dataset):
    def __init__(self, data, labels):
        self.data = np.asarray(data, dtype=np.float32)
        self.labels = np.asarray(labels, dtype=np.int64)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        x = torch.tensor(self.data[idx], dtype=torch.float32)
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        return x, y


def get_label_from_filename(file_name):

    lower_name = file_name.lower()
    return 1 if "fall" in lower_name else 0


def create_windows_from_file(file_path, label, seq_len):

    frames = np.load(file_path)

    if len(frames) < seq_len:
        return [], []

    windows = []
    labels = []

    step = 2 if label == 1 else 10

    for i in range(0, len(frames) - seq_len + 1, step):
        seq = frames[i:i + seq_len]

        if seq.shape != (seq_len, INPUT_SIZE):
            continue

        seq = normalize_sequence(seq)

        windows.append(seq)
        labels.append(label)

    return windows, labels


def load_feature_files(features_dir):

    if not os.path.exists(features_dir):
        raise FileNotFoundError(f"Папка features не найдена: {features_dir}")

    file_paths = []
    labels = []

    for file_name in sorted(os.listdir(features_dir)):
        if not file_name.lower().endswith(".npy"):
            continue

        file_path = os.path.join(features_dir, file_name)
        label = get_label_from_filename(file_name)

        file_paths.append(file_path)
        labels.append(label)

    if len(file_paths) == 0:
        raise RuntimeError("В папке features нет .npy файлов. Сначала запустите extract_features.py")

    return file_paths, np.array(labels, dtype=np.int64)


def build_dataset_from_files(file_paths, file_labels, seq_len):

    all_windows = []
    all_labels = []

    fall_count = 0
    normal_count = 0

    for file_path, label in zip(file_paths, file_labels):
        windows, labels = create_windows_from_file(file_path, label, seq_len)

        all_windows.extend(windows)
        all_labels.extend(labels)

        if label == 1:
            fall_count += len(labels)
        else:
            normal_count += len(labels)

    all_windows = np.array(all_windows, dtype=np.float32)
    all_labels = np.array(all_labels, dtype=np.int64)

    return all_windows, all_labels, fall_count, normal_count


def split_files_train_val(file_paths, labels):

    unique_classes, class_counts = np.unique(labels, return_counts=True)

    can_stratify = (
        len(unique_classes) == NUM_CLASSES
        and np.min(class_counts) >= 2
        and len(file_paths) >= 4
    )

    stratify_labels = labels if can_stratify else None

    train_files, val_files, train_labels, val_labels = train_test_split(
        file_paths,
        labels,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=stratify_labels
    )

    return train_files, val_files, train_labels, val_labels


def calculate_class_weights(labels):

    counts = np.bincount(labels, minlength=NUM_CLASSES)

    if np.any(counts == 0):
        print("Предупреждение: один из классов отсутствует в train. class_weights не используются.")
        return None

    total = counts.sum()
    weights = total / (NUM_CLASSES * counts)

    return torch.tensor(weights, dtype=torch.float32).to(device)


def train_one_epoch(model, train_loader, criterion, optimizer):
    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, targets in train_loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()

        outputs = model(inputs)
        loss = criterion(outputs, targets)

        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)

        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

    epoch_loss = running_loss / total
    epoch_acc = correct / total * 100.0

    return epoch_loss, epoch_acc


def evaluate(model, data_loader, criterion):
    model.eval()

    running_loss = 0.0
    correct = 0
    total = 0

    all_preds = []
    all_targets = []

    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            running_loss += loss.item() * inputs.size(0)

            _, predicted = outputs.max(1)

            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    epoch_loss = running_loss / total
    epoch_acc = correct / total * 100.0

    return epoch_loss, epoch_acc, all_targets, all_preds


def main():
    file_paths, file_labels = load_feature_files(FEATURES_DIR)

    print(f"\nНайдено файлов признаков: {len(file_paths)}")
    print(f"Файлов Fall: {np.sum(file_labels == 1)}")
    print(f"Файлов Normal: {np.sum(file_labels == 0)}")

    train_files, val_files, train_file_labels, val_file_labels = split_files_train_val(
        file_paths,
        file_labels
    )

    print(f"\nTrain файлов: {len(train_files)}")
    print(f"Validation файлов: {len(val_files)}")

    X_train, y_train, train_fall_windows, train_normal_windows = build_dataset_from_files(
        train_files,
        train_file_labels,
        SEQ_LEN
    )

    X_val, y_val, val_fall_windows, val_normal_windows = build_dataset_from_files(
        val_files,
        val_file_labels,
        SEQ_LEN
    )

    if len(X_train) == 0:
        raise RuntimeError("Train dataset пустой. Проверьте длину видео и SEQ_LEN.")

    if len(X_val) == 0:
        raise RuntimeError("Validation dataset пустой. Добавьте больше данных или уменьшите SEQ_LEN.")

    print("\nЗагрузка окон завершена!")
    print(f"Train окон всего: {len(X_train)}")
    print(f"|--- Train Fall: {train_fall_windows}")
    print(f"|--- Train Normal: {train_normal_windows}")

    print(f"\nValidation окон всего: {len(X_val)}")
    print(f"|--- Validation Fall: {val_fall_windows}")
    print(f"|--- Validation Normal: {val_normal_windows}")

    train_dataset = SkeletonWindowDataset(X_train, y_train)
    val_dataset = SkeletonWindowDataset(X_val, y_val)

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False
    )

    model = FallDetectionLSTM(
        input_size=INPUT_SIZE,
        hidden_size=HIDDEN_SIZE,
        num_classes=NUM_CLASSES
    ).to(device)

    class_weights = calculate_class_weights(y_train)

    if class_weights is not None:
        print(f"\nClass weights: {class_weights.detach().cpu().numpy()}")
        criterion = nn.CrossEntropyLoss(weight=class_weights)
    else:
        criterion = nn.CrossEntropyLoss()

    optimizer = optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    best_val_loss = float("inf")
    best_model_state = None

    print("\nСтарт обучения...")

    for epoch in range(EPOCHS):
        train_loss, train_acc = train_one_epoch(
            model,
            train_loader,
            criterion,
            optimizer
        )

        val_loss, val_acc, val_targets, val_preds = evaluate(
            model,
            val_loader,
            criterion
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = copy.deepcopy(model.state_dict())

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(
                f"Эпоха [{epoch + 1}/{EPOCHS}] | "
                f"Train Loss: {train_loss:.4f} | "
                f"Train Acc: {train_acc:.2f}% | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Acc: {val_acc:.2f}%"
            )

    if best_model_state is not None:
        model.load_state_dict(best_model_state)

    final_val_loss, final_val_acc, final_targets, final_preds = evaluate(
        model,
        val_loader,
        criterion
    )

    print("\nФинальная проверка на Validation:")
    print(f"Validation Loss: {final_val_loss:.4f}")
    print(f"Validation Accuracy: {final_val_acc:.2f}%")

    print("\nClassification report:")
    print(
        classification_report(
            final_targets,
            final_preds,
            target_names=["Normal", "Fall"],
            zero_division=0
        )
    )

    print("Confusion matrix:")
    print(confusion_matrix(final_targets, final_preds))

    torch.save(model.state_dict(), MODEL_SAVE_PATH)

    print(f"\nЛучшая модель сохранена в файл: {MODEL_SAVE_PATH}")


if __name__ == "__main__":
    main()