# Fall Detection System

This project is a fall detection system based on computer vision and deep learning.

The system analyzes a video of a person, detects the human skeleton using YOLOv8 Pose, and then uses an LSTM neural network to decide whether a fall happened or not.

## Project Idea

The pipeline is:

```text
Video / Camera
      ↓
YOLOv8 Pose
      ↓
Human keypoints extraction
      ↓
Sequence of 30 frames
      ↓
LSTM model
      ↓
Result: SAFE or FALL DETECTED

fall-detection-project/
├── backend/
│   ├── app.py
│   ├── fall_detector.py
│   ├── extract_features.py
│   ├── train_lstm.py
│   ├── live_demo.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── dataset/
├── features/
├── help_doc.txt
├── README.md
└── .gitignore

dataset/
features/
*.npy
*.pth
*.pt
*.mp4
*.mov
*.avi
*.webm