# InvigiLens: Start-to-Finish System Build Plan

**Project Goal:** Design, implement, train, and deploy the full InvigiLens system (Smart, Real-Time Malpractice Detection and Monitoring System for offline exams) from scratch.

**Core Technology Stack:** Python, OpenCV, YOLOv8, MediaPipe Face Mesh.
**Technical Target:** Maintain an inference speed of **35-40 FPS** to ensure real-time performance.

---

## Phase 1: Model Integration & Validation (Refined)

### 1.1 Model Ingestion
- **Current State:** User has provided a pre-trained **YOLOv8 Malpractice Detection Model** (Object Detection, not Pose).
- **Activity:** Locate and load the model (`.pt` file). Verify its classes.
- **Goal:** Confirm it can detect core classes (e.g., 'mobile', 'cheating', 'person').

### 1.2 Capability Assessment
- **Activity:** Run inference on sample images/video to gauge performance.
- **Gap Analysis:** Determine if the model covers "leaning" and "sharing answers" as specific classes. If not, we will augment it with **MediaPipe Pose** or heuristic logic in Phase 2.


---

## Phase 2: Core System Implementation (Logic & Pipeline)

### 2.1 Model Optimization and Initialization
- **Activity:** Convert the user's model into an optimized format (ONNX/TensorRT) if needed for speed.
- **Activity:** Initialize **MediaPipe Face Mesh** for Head Pose Estimation (Gaze Tracking).
- **Decision Point:** If the custom YOLO model lacks body pose info, integrate **MediaPipe Pose** or use geometric heuristics for body orientation.

### 2.2 Hybrid Inference Engine
- **Activity:** Build the pipeline to run:
    1.  **Custom YOLOv8** (Objects/Malpractice Actions).
    2.  **MediaPipe Face Mesh** (Gaze: Yaw/Pitch).
    3.  *(Optional)* **MediaPipe Pose** (if needed for 'Leaning').
- **Activity:** Implement a **Multi-Object Tracking (MOT)** mechanism to assign and maintain a **Unique, Persistent Student ID** for every person across the entire video sequence.

### 2.3 Behavioral Logic Engine (BLE) Construction
- **Activity:** Implement the central **Behavioral Logic Engine** to analyze numerical outputs from the Dual Inference Layer.
- **Activity:** **Define and hardcode the final heuristic thresholds** required for detection:
    - **Angular Thresholds (Gaze):** $\theta_{Y}$ (Max Yaw) and $\theta_{P}$ (Max Pitch).
    - **Distance Thresholds (Proximity):** $\delta$ (Proximity) and $\delta_{contact}$ (Hand-to-Hand).
    - **Confidence Threshold (Object):** $\gamma$ (Min object confidence).

### 2.4 Temporal Rule Logic
- **Activity:** Implement the crucial temporal logic to track the sustained duration ($t$) of a violation for each unique Student ID.
- **Logic Mandate:** An alert is triggered **only if** the instantaneous violation (e.g., $|Yaw| > \theta_{Y}$) persists for **$t > 15$ frames**.
- **Deliverable:** Functional temporal filter integrated into the BLE.

---

## Phase 3: Output, Alerting, and Dashboard

### 3.1 Real-Time Visual Feedback
- **Activity:** Configure OpenCV to render the final processed video stream. Overlay the frame with:
    - Bounding boxes and **Persistent Student IDs**.
    - A distinct, high-contrast **Alert Text Overlay** displaying the `Violation Type` (e.g., "GAZE DEVIATION") only when a *Confirmed Violation* is logged.

### 3.2 Persistent Log System (Privacy-First)
- **Activity:** Develop the final logging module to append confirmed incidents to a **.csv** file. This log must be the single source of truth for all alerts.
- **Required Fields:** `Timestamp`, `Student ID`, `Violation Type`, and `Confidence Score`.

### 3.3 Invigilator Dashboard Deployment
- **Activity:** Develop the client-facing **Dashboard UI** (using web frameworks).
- **Mandatory Display Elements:**
    - The live video feed (from 3.1).
    - A scrolling, filterable list/table of all **Confirmed Alerts** (read dynamically from the log file in 3.2).

---

## Phase 4: Final Validation and Delivery

### 4.1 Comprehensive Stress Testing
- **Activity:** Conduct rigorous end-to-end testing against large volumes of unseen video footage. Validate system stability, test the robustness of the Multi-Object Tracking (MOT), and confirm that the target **35-40 FPS** performance is achieved under full load.

### 4.2 Threshold Final Tuning
- **Activity:** Perform final iterative adjustment of all BLE thresholds ($\theta$, $\delta$, $t$) to ensure the system successfully detects all true positives while minimizing the False Positive Rate from innocent student actions.

### 4.3 Documentation and Delivery
- **Activity:** Finalize the codebase, prepare technical documentation, and ensure all components are ready for final presentation and project defense.

---

## Abstract

InvigiLens: A Smart, Real-Time Malpractice Detection and Monitoring System is designed to address the growing challenges of maintaining academic integrity during offline examinations, especially in crowded halls with limited supervision. Existing AI-based solutions often rely solely on video input, lack real-time responsiveness, and overlook issues such as impersonation and verbal cheating.

The system uses YOLOv8 to detect suspicious objects and MediaPipe/OpenPose to identify abnormal gestures or hand movements. It supports invigilator-free communication by recognizing hand-raising gestures for assistance. FaceNet is used for facial recognition to verify student identity and to automate attendance.

With multi-camera integration, the system ensures full exam hall coverage. Suspicious behavior triggers real-time alerts with video clips, flag details, and student information, sent directly to the invigilator's dashboard. Only flagged incidents are stored, ensuring privacy and ethical compliance.

Aligned with SDG 4: Quality Education, InvigiLens promotes fairness, transparency, and accountability in academic environments. It is scalable, affordable, and ready for deployment across schools, universities, and competitive exam centers.
