import os

# System Configuration
CONFIDENCE_THRESHOLD = 0.5  # Base threshold for detection

# Model Paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/best.pt')

# Class Definitions (from user's data.yaml)
CLASS_NAMES = {
    0: 'Giving object',
    1: 'Giving signal',
    2: 'Looking Friend',
    3: 'Moving',
    4: 'Normal',
    5: 'Using Phone'
}

# Alert Logic Configuration
# Thresholds for heuristic detection (MediaPipe)
GAZE_YAW_THRESHOLD = 20  # Degrees
GAZE_PITCH_THRESHOLD = 15 # Degrees
SUSTAINED_FRAME_COUNT = 15 # Number of frames condition must persist to trigger alert

# Colors for Visualization (BGR)
COLORS = {
    'Normal': (0, 255, 0),
    'Suspicious': (0, 165, 255), # Orange
    'Violation': (0, 0, 255),    # Red
    'Text': (255, 255, 255)
}
