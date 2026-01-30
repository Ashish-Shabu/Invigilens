# InvigiLens: Advanced Autonomous Malpractice Detection System
## Technical Project Report

---

### 1. Executive Summary
**InvigiLens** is a real-time, sophisticated automated proctoring system designed to maintain academic integrity in offline examination environments. Unlike traditional CCTV systems that require passive human monitoring, InvigiLens continuously analyzes video feeds using a hybrid Artificial Intelligence pipeline. It detects specific malpractice behaviors (e.g., passing objects, using phones, unauthorized communication), tracks student gaze for suspicious head movements, and automates attendance via facial recognition. The system operates on an "Alert-Only" philosophy, respecting privacy by only permanently recording and logging incidents where a verified violation occurs.

### 2. System Architecture
The system follows a **Event-Driven Microservices Architecture**, consisting of three distinct layers:

1.  **Perception Layer (ML Engine)**: A Python-based computer vision pipeline that processes raw video frames, runs inference across multiple neural networks, and executes heuristic logic.
2.  **Logic & Communication Layer (Backend)**: A Node.js/Express server that acts as the central message broker. It receives alerts from the ML Engine via HTTP/Socket.io and broadcasts them to the dashboard. It also manages persistence via MongoDB.
3.  **Presentation Layer (Dashboard)**: A responsive web interface for invigilators to view live feeds, receive real-time pop-up alerts, and review historical evidence clips.

---

### 3. Technology Stack

#### A. Machine Learning & Computer Vision
*   **Language**: Python 3.10+
*   **Core Vision Library**: OpenCV (`cv2`) for frame manipulation, buffer management, and video encoding.
*   **Object Detection**: `Ultralytics YOLOv8` (You Only Look Once).
    *   *Custom Model*: Fine-tuned on a proprietary dataset for specific malpractice classes.
    *   *Standard Model*: YOLOv8n (COCO) used as a secondary validator for specific objects like "Cell Phones".
*   **Pose Estimation**: `YOLO-Pose` for keypoint detection (Nose, Ears, Eyes) to derive head orientation.
*   **Face Recognition**: `DeepFace` (utilizing the **FaceNet** model backbone) for student identification.
*   **Vector Math**: `NumPy` and `SciPy` for geometric calculations and cosine similarity metrics.

#### B. Backend Infrastructure
*   **Runtime**: Node.js
*   **Framework**: Express.js (REST API).
*   **Real-Time Protocol**: `Socket.io` (WebSockets) for low-latency video streaming and alert broadcasting.
*   **Database**: MongoDB (via `Mongoose` ODM) for structured storage of alerts and student records.
*   **Storage**: Local file system for high-bandwidth video evidence (`.mp4` clips).

#### C. Frontend Interface
*   **Core**: HTML5, CSS3, Vanilla JavaScript (ES6+).
*   **Design**: Custom CSS for high-contrast "Dark Mode" monitoring UI.
*   **Streaming**: Base64 frame rendering via WebSocket events.
*   **Dynamic UI**: DOM manipulation for real-time alert injection without page reloads.

---

### 4. Technical Specifications & Algorithms

#### A. Multi-Stage Inference Pipeline
The system does not rely on a single model. It uses a **Cascade Logic** to minimize false positives:

1.  **Primary Object Detection Phase**:
    *   Input: Resize frame to $640 \times 640$.
    *   Model: Custom YOLOv8.
    *   **Classes Detected**: `Giving object`, `Giving signal`, `Looking Friend`, `Moving`, `Normal`, `Using Phone`.
    *   **Confidence Threshold ($\gamma$)**: $0.45$.
    *   *Logic*: Detections with $Confidence < \gamma$ are discarded immediately.

2.  **Secondary Phone Validation**:
    *   Parallel execution of Standard YOLOv8n (COCO Class 67: Cell Phone).
    *   *Rule*: If the Custom Model is unsure, but the Standard Model detects a "Cell Phone" with $>0.40$ confidence, the "Using Phone" violation is enforced.

3.  **Geometric Head Gaze Estimation (The "Gaze Formula")**:
    *   Instead of heavy 3D gaze models, we implement a lightweight geometric derivation using 2D Facial Keypoints from YOLO-Pose.
    *   **Keypoints**: $Nose (x_n, y_n)$, $LeftEar (x_l, y_l)$, $RightEar (x_r, y_r)$.
    *   **Euclidean Distances**:
        $$d_L = |x_n - x_l|$$
        $$d_R = |x_n - x_r|$$
    *   **The Ratio Logic**: Since the head is a rigid body, turning left hides the left ear and exposes the right ear (increasing $d_R$ relative to $d_L$).
    *   **Thresholds**:
        *   **Looking Left**: If $\frac{d_L}{d_R} < 0.45$
        *   **Looking Right**: If $\frac{d_R}{d_L} < 0.45$
    *   *Priority*: This geometric logic overrides the semantic "Looking" label from the object detector if there is a conflict, significantly reducing false positives from students simply resting their heads.

4.  **Identity Verification (FaceNet)**:
    *   **Embedding**: 128-dimensional vector representation of the face.
    *   **Metric**: Cosine Distance.
        $$Distance(A, B) = 1 - \frac{A \cdot B}{||A|| \cdot ||B||}$$
    *   **Threshold**: $0.6$ (Strict match required).
    *   *Operational Frequency*: Ran every 2.0 seconds (not every frame) to preserve system FPS.

#### B. Temporal Incident Recording (State Machine)
To avoid spamming unrelated frames, the system uses a temporal state machine:
1.  **State: IDLE**:
    *   Buffer last 30 frames (1 second) in a sliding window (`deque`).
    *   Upon First Detection $\rightarrow$ Switch to **RECORDING**. Capture `Start Timestamp`.
2.  **State: RECORDING**:
    *   Append current frames to the evidence buffer.
    *   **Cooldown Logic**: If detection stops, increment `Cooldown Counter`.
    *   **Commit Condition**: If `Cooldown > 30 frames` (1 second of silence) OR `Duration > 30 seconds`.
    *   **Action**: Save buffered frames to disk (`.mp4`, H.264 codec), Send Alert API Request, Switch to **IDLE**.

---

### 5. Database Schema
**Collection: Alerts**
| Field | Type | Description |
| :--- | :--- | :--- |
| `studentId` | String | Recognized Name or "Unknown" |
| `violationType` | String | Enum (`Using Phone`, `Giving object`, etc.) |
| `confidence` | Number | Maximum confidence score observed during the incident |
| `timestamp` | Date | ISO 8601 Timestamp of the incident start |
| `evidencePath` | String | Relative path to the saved `.mp4` video clip |
| `status` | String | `pending` (default), `verified`, `rejected` |

---

### 6. Operational Workflow
1.  **Initialization**:
    *   System loads recognized student faces into memory (embeddings).
    *   Establishes Socket connection to Backend.
2.  **Monitoring Loop**:
    *   Captures frame $F_t$.
    *   Runs Face Recognition (Async, 0.5Hz).
    *   Runs YOLO Detection + Pose Estimation.
    *   **Logic Filter**: Checks Gaze Ratio and Class Confidence.
    *   **Visualizer**: Draws Bounding Boxes (Red for Violation, Green for Normal).
    *   **Stream**: Encodes $F_t$ to JPEG $\rightarrow$ Base64 $\rightarrow$ Emits to Dashboard.
3.  **Incident Handling**:
    *   If Violation Detected: Locks Tracking on Student.
    *   On Violation End: Asynchronously POSTs payload to `/api/alerts`.
4.  **Dashboard Update**:
    *   Server receives POST.
    *   Saves to MongoDB.
    *   Emits `new_alert` event to Frontend.
    *   Invigilator hears audio chime and sees new card in "Live Alerts" panel.

---

### 7. Future Scope & Scalability
*   **Multi-Camera Support**: The backend is designed to be stateless and can accept connections from multiple ML Engine instances running on different edge devices (Raspberry Pi / Jetson Nano), allowing for coverage of large examination halls.
*   **Behavioral Forensics**: Future updates could include long-term statistical analysis of student behavior to identify subtle cheating patterns over the course of the entire exam duration.
