import cv2
import os
import time

import queue
import threading
from ultralytics import YOLO
import requests
import numpy as np
from .config import CLASS_NAMES, MODEL_PATH, CONFIDENCE_THRESHOLD, GAZE_YAW_THRESHOLD, GAZE_PITCH_THRESHOLD

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("Warning: MediaPipe not available (likely Python version issue). Gaze tracking disabled.")

import socketio
import base64




class MalpracticeDetector:
    def __init__(self, model_path=MODEL_PATH):
        """
        Initialize the Object Detection (YOLO) and Pose/Face Estimation (MediaPipe) models.
        """
        print(f"Loading YOLO model from: {model_path}")
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None

        # MediaPipe Face Mesh for Gaze Detection
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
                refine_landmarks=True
            )
        else:
            self.face_mesh = None

        
        # Internal State
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.api_url = "http://localhost:5000/api/alerts"
        
        # Incident Management
        self.violation_state = 'IDLE' # IDLE, RECORDING
        self.current_violation_label = None
        self.violation_frame_buffer = [] # To store frames for the video
        self.buffer_size = 30 * 1 # Keep 1 second of pre-context (at 30fps)
        self.sliding_window = [] # Always keep last N frames
        self.recording_start_time = 0
        self.monitoring_active = False # Default to False as requested

        self.cooldown_frames = 0
        
        # Socket.io for Streaming
        self.sio = socketio.Client()
        
        @self.sio.on('set_monitoring')
        def on_monitor_change(data):
            self.monitoring_active = data['active']
            state = "ON" if self.monitoring_active else "OFF"
            print(f"Monitoring Toggled: {state}")

        @self.sio.on('camera_control')
        def on_camera_control(data):
            # data = {'cnt': 'start'} or {'cnt': 'stop'}
            if data.get('action') == 'start':
                self.camera_active = True
                print("Received Camera START command.")
            elif data.get('action') == 'stop':
                self.camera_active = False
                print("Received Camera STOP command.")

        try:

            self.sio.connect('http://localhost:5000')

            print("Connected to Express Socket Server")
        except Exception as e:
            print(f"Socket connection failed: {e}")

    def get_head_pose(self, frame):
        """
        Estimate head pose (Yaw, Pitch, Roll) using MediaPipe Face Mesh and PnP.
        """
        if not self.face_mesh:
            return None, None, None

        img_h, img_w, _ = frame.shape

        results = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                face_3d = []
                face_2d = []

                # Extract relevant landmarks (nose, chin, eyes, mouth)
                landmark_indices = [33, 263, 1, 61, 291, 199] 
                
                for idx, lm in enumerate(face_landmarks.landmark):
                    if idx in landmark_indices:
                        x, y = int(lm.x * img_w), int(lm.y * img_h)
                        face_2d.append([x, y])
                        face_3d.append([x, y, lm.z])
                
                face_2d = np.array(face_2d, dtype=np.float64)
                face_3d = np.array(face_3d, dtype=np.float64)

                # Camera matrix estimation
                focal_length = 1 * img_w
                cam_matrix = np.array([ [focal_length, 0, img_h / 2],
                                        [0, focal_length, img_w / 2],
                                        [0, 0, 1]])
                dist_matrix = np.zeros((4, 1), dtype=np.float64)

                success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)

                if success:
                    rmat, jac = cv2.Rodrigues(rot_vec)
                    angles, mtxR, mtxQ, Q, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)
                    return angles[0] * 360, angles[1] * 360, (face_2d[0][0], face_2d[0][1])
        
        return None, None, None

    def save_incident_clip(self, label, frames):
        """
        Save the buffered frames as a video clip (.mp4) and return filename.
        """
        if not frames:
            return None
            
        timestamp = int(time.time() * 1000)
        # Reverting to .mp4 with mp4v as vp80 failed on Windows env
        filename = f"{label.replace(' ', '_')}_{timestamp}.mp4"
        # Adjusted path to match project structure
        save_path = os.path.join(os.path.dirname(__file__), '../../data/processed', filename)
        
        height, width, _ = frames[0].shape
        # Using 'avc1' (H.264) which is standard for HTML5 video
        # If this fails, we might need to download openh264-1.8.0-win64.dll
        fourcc = cv2.VideoWriter_fourcc(*'avc1') 
        out = cv2.VideoWriter(save_path, fourcc, 20.0, (width, height))


        
        for f in frames:
            out.write(f)
        out.release()
        
        return filename


    def send_alert(self, label, confidence, evidence_filename):
        """
        Send alert to Backend API asynchronously with video evidence.
        """
        def _send():
            try:
                payload = {
                    "studentId": "Student_1",
                    "violationType": label,
                    "confidence": float(confidence),
                    "evidencePath": evidence_filename if evidence_filename else ""
                }
                requests.post(self.api_url, json=payload, timeout=2)
            except Exception as e:
                print(f"Failed to log alert: {e}")
        
        threading.Thread(target=_send).start()


    def predict(self, frame):
        """
        Run inference and return detection results.
        """
        results = []
        if self.model:
            yolo_results = self.model(frame, verbose=False, conf=CONFIDENCE_THRESHOLD)[0]
            for box in yolo_results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = CLASS_NAMES.get(cls_id, "Unknown")
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                results.append({
                    "type": "object",
                    "label": label,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2)
                })

        # Head Pose
        pitch, yaw, nose_coord = self.get_head_pose(frame)
        if pitch is not None and yaw is not None:
             if abs(yaw) > GAZE_YAW_THRESHOLD:
                violation = "Looking Left" if yaw < 0 else "Looking Right"
                results.append({
                    "type": "pose",
                    "label": violation,
                    "confidence": 1.0,
                    "bbox": None
                })
        
        return results

    def start_service(self):
        """
        Main Service Loop: Waits for 'camera_control' start command to open camera.
        """
        self.camera_active = False # Start offline
        cap = None

        print("Service Started. Waiting for Website to load (Camera Start Signal)...")
        
        while True:
            # 1. Check Camera State
            if self.camera_active:
                if cap is None or not cap.isOpened():
                    print("Opening Camera...")
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                         print("Failed to open camera.")
                         self.camera_active = False
                         time.sleep(1)
                         continue
                
                # 2. Read Frame
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame")
                    time.sleep(0.1)
                    continue

                # 3. Process (buffer, detect, logic)
                # --- pre-process buffer ---
                self.sliding_window.append(frame.copy())
                if len(self.sliding_window) > self.buffer_size:
                    self.sliding_window.pop(0)

                # --- Detection (Only if Monitoring is Active) ---
                detections = []
                if self.monitoring_active:
                    detections = self.predict(frame)
                
                # --- Logic Engine ---
                detected_violation = None
                
                # Check for any malpractice class
                malpractice_classes = ['Using Phone', 'Giving object', 'Giving signal', 'Looking Friend', 'Looking Left', 'Looking Right']
                
                for det in detections:
                    if det['label'] in malpractice_classes:
                        detected_violation = det['label']
                        break 
                
                # State Machine
                if self.violation_state == 'IDLE':
                    if detected_violation:
                        self.violation_state = 'RECORDING'
                        self.current_violation_label = detected_violation
                        self.recording_start_time = time.time()
                        self.violation_frame_buffer = list(self.sliding_window)
                        self.cooldown_frames = 0
                        print(f"Violation Started: {detected_violation}")

                elif self.violation_state == 'RECORDING':
                    self.violation_frame_buffer.append(frame.copy())
                    if detected_violation:
                         self.cooldown_frames = 0
                    else:
                        self.cooldown_frames += 1
                    
                    elapsed = time.time() - self.recording_start_time
                    if self.cooldown_frames > 30 or elapsed > 30.0:
                        print(f"Violation Ended. Saving clip...")
                        filename = self.save_incident_clip(self.current_violation_label, self.violation_frame_buffer)
                        if filename:
                            self.send_alert(self.current_violation_label, 0.95, filename)
                        self.violation_state = 'IDLE'
                        self.violation_frame_buffer = []
                        self.current_violation_label = None

                # --- Visualization & Streaming ---
                for det in detections:
                    if det['bbox']:
                        x1, y1, x2, y2 = det['bbox']
                        label_text = f"{det['label']} {det['confidence']:.2f}"
                        color = (0, 0, 255) if det['label'] in malpractice_classes else (0, 255, 0)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                if self.violation_state == 'RECORDING':
                    cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1)
                    cv2.putText(frame, "REC", (50, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                try:
                    small_frame = cv2.resize(frame, (640, 480)) 
                    _, buffer = cv2.imencode('.jpg', small_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    b64_frame = base64.b64encode(buffer).decode('utf-8')
                    if self.sio.connected:
                        self.sio.emit('video_frame', b64_frame)
                except:
                    pass

                time.sleep(0.01)



            else:
                # Camera NOT active
                if cap is not None:
                    cap.release()
                    cap = None
                    print("Camera Released (Waiting for Website).")
                
                # Sleep to prevent high CPU usage while idle
                time.sleep(0.5)






if __name__ == "__main__":
    # Test run
    detector = MalpracticeDetector()
    detector.start_service()


