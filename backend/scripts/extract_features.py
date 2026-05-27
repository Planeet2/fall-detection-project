import os
import cv2
import numpy as np
from ultralytics import YOLO

MODEL_NAME = "yolov8n-pose.pt"

DATASET_PATH = "./dataset/"
OUTPUT_PATH = "./features/"

INPUT_SIZE = 51  



if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)


model = YOLO(MODEL_NAME)


def get_best_person_keypoints(yolo_result):

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


def process_folder(folder_path):
    video_features = []

    images = sorted([
        img for img in os.listdir(folder_path)
        if img.lower().endswith((".png", ".jpg", ".jpeg"))
    ])

    for img_name in images:
        img_path = os.path.join(folder_path, img_name)
        frame = cv2.imread(img_path)

        if frame is None:
            print(f"Предупреждение: не удалось прочитать изображение: {img_path}")
            continue

        results = model(frame, verbose=False)

        if len(results) > 0:
            keypoints = get_best_person_keypoints(results[0])

            if keypoints is not None:
                frame_features = keypoints.flatten()

                if len(frame_features) == INPUT_SIZE:
                    video_features.append(frame_features)
                else:
                    video_features.append([0.0] * INPUT_SIZE)
            else:
                video_features.append([0.0] * INPUT_SIZE)
        else:
            video_features.append([0.0] * INPUT_SIZE)

    return np.array(video_features, dtype=np.float32)


def main():
    if not os.path.exists(DATASET_PATH):
        print(f"Ошибка: папка dataset не найдена: {DATASET_PATH}")
        return

    folders = sorted(os.listdir(DATASET_PATH))

    if len(folders) == 0:
        print("Ошибка: папка dataset пустая.")
        return

    for folder_name in folders:
        folder_path = os.path.join(DATASET_PATH, folder_name)

        if not os.path.isdir(folder_path):
            continue

        print(f"Обработка папки: {folder_name}...")

        np_features = process_folder(folder_path)

        if len(np_features) == 0:
            print(f"Пропуск: в папке {folder_name} не найдено кадров.")
            continue

        output_file = os.path.join(OUTPUT_PATH, f"{folder_name}.npy")
        np.save(output_file, np_features)

        print(f"Успешно сохранено: {output_file} | Размер: {np_features.shape}")

    print("\nВсе видео успешно обработаны через YOLOv8 Pose!")


if __name__ == "__main__":
    main()