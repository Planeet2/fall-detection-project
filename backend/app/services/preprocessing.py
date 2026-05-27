import numpy as np

from app.config import INPUT_SIZE


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
