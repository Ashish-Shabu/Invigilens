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
from deepface import DeepFace
import pandas as pd
import socketio
import base64
from deepface import DeepFace
import pandas as pd
# import google.generativeai as genai # Cloud AI Disabled




class MalpracticeDetector:
    def __init__(self, model_path=MODEL_PATH):
        """
        Initialize the Object Detection (YOLO) and Pose/Face Estimation (MediaPipe) models.
        """
        print(f"Loading YOLO model from: {model_path}")
        try:
            self.model = YOLO(model_path)
            print(f"Loading YOLO model from: {model_path}")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.model = None

        # --- STANDARD MODEL FOR PHONE DETECTION ---
        try:
            phone_model_path = os.path.join(os.path.dirname(__file__), '../models/invigilens_phone.pt')
            self.phone_model = YOLO(phone_model_path) 
            print("Loading Standard for Phone Backup...")
        except Exception as e:
            print(f"Error loading Standard YOLO: {e}")
            self.phone_model = None

        # --- YOLO POSE FOR HEAD GAZE ---
        try:
            pose_model_path = os.path.join(os.path.dirname(__file__), '../models/invigilens_pose.pt')
            self.pose_model = YOLO(pose_model_path)
            print("Loading Pose for Head Gaze...")
        except Exception as e:
            print(f"Error loading YOLO-Pose model: {e}")
            self.pose_model = None

        # MediaPipe Face Mesh for Gaze Detection
        global MEDIAPIPE_AVAILABLE
        if MEDIAPIPE_AVAILABLE:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5,
                    refine_landmarks=True
                )
            except Exception as e:
                print(f"Warning: MediaPipe Initialization Failed ({e}). Gaze tracking disabled.")
                self.face_mesh = None
                MEDIAPIPE_AVAILABLE = False
        else:
            self.face_mesh = None

        
        # Internal State
        self.frame_queue = queue.Queue(maxsize=1)
        self.running = False
        self.api_url = "http://localhost:5000/api/alerts"
        
        # Incident Management
        self.violation_state = 'IDLE' # IDLE, RECORDING
        self.current_violation_label = None
        self.violation_student_id = "Unknown" # Track who is committing the violation
        self.violation_frame_buffer = [] # To store frames for the video
        self.buffer_size = 30 * 1 # Keep 1 second of pre-context (at 30fps)
        self.sliding_window = [] # Always keep last N frames
        self.sliding_window = [] # Always keep last N frames
        self.recording_start_time = 0
        
        # Face Recognition State
        self.known_face_encodings = []
        self.known_face_names = []
        self.frame_count = 0
        self.current_student_name = "Scanning..."
        self.last_recognition_time = time.time()
        
        # Load faces immediately
        self.load_known_faces()
        self.monitoring_active = False # Default to False as requested

        self.monitoring_active = False # Default to False as requested
        self.current_max_confidence = 0.0 # Track max confidence during an incident

        self.cooldown_frames = 0
        
        # --- CLOUD AI DISABLED (Reverted to Local Model) ---
        self.gemini_model = None
        self.ai_result = "Normal"
        self.ai_confidence = 0.0

        
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

    def load_known_faces(self):
        """
        Load student images from data/students/ and pre-compute embeddings
        """
        print("Loading student faces...")
        students_dir = os.path.join(os.path.dirname(__file__), '../../data/students')
        if not os.path.exists(students_dir):
            os.makedirs(students_dir)
            
        for filename in os.listdir(students_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(students_dir, filename)
                name = os.path.splitext(filename)[0] # Roll No or Name
                try:
                    # Using Facenet for speed/accuracy balance
                    # We only need the embedding once
                    embeddings = DeepFace.represent(img_path=filepath, model_name="Facenet", enforce_detection=False)
                    if embeddings:
                        embedding = embeddings[0]['embedding']
                        self.known_face_encodings.append(embedding)
                        self.known_face_names.append(name)
                        print(f"Loaded face: {name}")
                except Exception as e:
                    print(f"Could not load face {filename}: {e}")
        print(f"Total students loaded: {len(self.known_face_encodings)}")
        
    def recognize_face_in_frame(self, frame):
        """
        Periodically check identity of person in frame
        """
        # Only run every 2 seconds to save FPS
        if time.time() - self.last_recognition_time < 2.0:
            return self.current_student_name
            
        self.last_recognition_time = time.time()
        
        try:
            # Detect face in current frame
            # Enforce detection=False prevents crash if no face found, but returns full image embedding which is bad.
            # Ideally we want face.
            # Let's try to extract face area first? No, DeepFace handles it.
            
            # Use 'FastMTCNN' or just 'opencv' backend for speed
            target_embeddings = DeepFace.represent(img_path=frame, model_name="Facenet", enforce_detection=False, detector_backend="opencv")
            
            if not target_embeddings:
                self.current_student_name = "Unknown"
                return "Unknown"
            
            target_embedding = target_embeddings[0]['embedding']
            
            # Match Threshold (0.4 is strict, 0.6 is balanced)
            threshold = 0.6 
            
            min_dist = 100
            best_match_index = -1
            
            from scipy.spatial.distance import cosine
            
            for i, known_emb in enumerate(self.known_face_encodings):
                dist = cosine(known_emb, target_embedding)
                if dist < min_dist:
                    min_dist = dist
                    best_match_index = i
            
            # Debug print
            # print(f"Dist: {min_dist} (Threshold: {threshold})")

            current_result = "Unknown"

            if min_dist < threshold:
                name = self.known_face_names[best_match_index]
                current_result = name
                self.current_student_name = name # Immediate update on success
                
                # Emit to dashboard
                if self.sio.connected:
                    self.sio.emit('attendance_update', {'name': name, 'status': 'Present'})
            else:
                # If unknown, don't flip immediately. Keep previous valid name for a bit
                # unless we are consistently unknown.
                self.current_student_name = "Unknown/Impersonator"
                if self.sio.connected:
                    self.sio.emit('attendance_update', {'name': 'Unknown', 'status': 'Alert'})
                    
        except Exception as e:
            # print(f"Recog Error: {e}")
            pass
            
        return self.current_student_name

    def get_pose_yolo(self, frame):
        """
        Estimate Left/Right looking using YOLO-Pose Keypoints (Nose, Eye, Ear).
        """
        if not self.pose_model: return None
        
        # Low confidence threshold (0.25) to ensure we get keypoints even in bad lighting
        results = self.pose_model(frame, verbose=False, conf=0.25)[0]
        if not results.keypoints: return None
        
        # Get Keypoints (x, y, conf)
        # 0: Nose, 1: Left Eye, 2: Right Eye, 3: Left Ear, 4: Right Ear
        kpts = results.keypoints.data[0].cpu().numpy()
        
        if len(kpts) < 5: return None
        
        nose = kpts[0]
        l_ear = kpts[3]
        r_ear = kpts[4]
        
        # Confidence check (Lowered to 0.3 for better detection in low light)
        if nose[2] < 0.3 or l_ear[2] < 0.3 or r_ear[2] < 0.3:
            return None # Not confident
            
        # Vectors
        nose_x = nose[0]
        l_ear_x = l_ear[0]
        r_ear_x = r_ear[0]
        
        dist_l = abs(nose_x - l_ear_x)
        dist_r = abs(nose_x - r_ear_x)
        
        # Logic: If looking left, right ear is far, left ear is close (or hidden)
        
        ratio = 0.0
        direction = "Straight"
        
        if dist_l == 0 or dist_r == 0: return "Unknown"
        
        # Relaxed Threshold: 0.60 allows easier detection of head turns
        if dist_l < dist_r:
            ratio = dist_l / dist_r
            if ratio < 0.60: direction = "Looking Left" 
        else:
            ratio = dist_r / dist_l
            if ratio < 0.60: direction = "Looking Right"
            
        return direction

    def detect_with_gemini(self, frame):
        """
        Send frame to Google Gemini 1.5 Flash for high-intelligence detection.
        """
        if not self.gemini_model: 
            return None, 0.0

        try:
            # Resize for bandwidth optimization (Gemini handles standard res well, but smaller is faster)
            # keeping it decent size for detail
            small_frame = cv2.resize(frame, (640, 480))
            
            # Convert to PIL Image (Gemini prefers PIL or pure bytes)
            from PIL import Image
            import io
            
            # OpenCV BGR -> RGB
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            
            prompt = "Act as a proctor. Is the student in this webcam frame doing any of these specific things? 1. Holding or using a Mobile Phone/Cell Phone. 2. Talking to another person. 3. Turning head completely away/looking away. Reply with ONLY ONE phrase: 'Using Phone', 'Talking', 'Looking Away', or 'Normal'."
            
            response = self.gemini_model.generate_content([prompt, pil_image])
            result = response.text.strip()
            
            print(f"GEMINI DEBUG: {result}") # DEBUG PRINT
            
            # Normalize Result
            if "Phone" in result: return "Using Phone", 0.98
            if "Taking" in result or "Talking" in result: return "Talking", 0.95
            if "Away" in result: return "Looking Away", 0.90
            
            return "Normal", 0.0
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None, 0.0

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
        # Reverting BACK to H.264 (avc1) because browser cannot play 'mp4v'
        # If this errors on Windows, the file might be corrupt, but user requested this specific codec.
        # Ideally needs 'openh264' DLL download.
        fourcc = cv2.VideoWriter_fourcc(*'avc1') 
        out = cv2.VideoWriter(save_path, fourcc, 20.0, (width, height))

        for f in frames:
            out.write(f)
        out.release()
        
        return filename


    def send_alert(self, label, confidence, evidence_filename, student_id):
        """
        Send alert to Backend API asynchronously with video evidence.
        """
        def _send():
            try:
                payload = {
                    "studentId": student_id,
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
            # CRITICAL: Lowered to 0.15 for DEMO purposes to ensure 'Giving Object' triggers
            yolo_results = self.model(frame, verbose=False, conf=0.15)[0]
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
        
        # --- SECONDARY CHECK: Standard YOLOv8n (COCO Class 67 = cell phone) ---
        if self.phone_model:
            # We use a lower threshold (0.40) because standard YOLO is usually quite accurate
            phone_results = self.phone_model(frame, verbose=False, conf=0.40)[0]
            for box in phone_results.boxes:
                cls_id = int(box.cls[0])
                if cls_id == 67: # 67 is 'cell phone' in COCO dataset
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    results.append({
                        "type": "object",
                        "label": "Using Phone", # Force the label
                        "confidence": float(box.conf[0]),
                        "bbox": (x1, y1, x2, y2)
                    })
        
        # --- SECONDARY CHECK: Standard YOLOv8n (COCO Class 67 = cell phone) ---
        if self.phone_model:
            # We use a lower threshold (0.40) because standard YOLO is usually quite accurate
            phone_results = self.phone_model(frame, verbose=False, conf=0.40)[0]
            for box in phone_results.boxes:
                cls_id = int(box.cls[0])
                if cls_id == 67: # 67 is 'cell phone' in COCO dataset
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    results.append({
                        "type": "object",
                        "label": "Using Phone", # Force the label
                        "confidence": float(box.conf[0]),
                        "bbox": (x1, y1, x2, y2)
                    })

        # Head Pose
        gaze_direction = self.get_pose_yolo(frame)
        if gaze_direction and gaze_direction != "Straight" and gaze_direction != "Unknown":
            results.append({
                "type": "pose",
                "label": gaze_direction,
                "confidence": 0.85, 
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

                # --- Standard Image Enhancement ---
                # The previous method (CLAHE) was distorting colors. 
                # Switching to simple linear enhancement for natural look.
                # alpha=1.1 (10% more contrast), beta=15 (slightly brighter)
                frame = cv2.convertScaleAbs(frame, alpha=1.1, beta=15)
                # -----------------------------------

                # --- 3. Process (buffer, detect, logic)


                # --- pre-process buffer ---
                self.sliding_window.append(frame.copy())
                if len(self.sliding_window) > self.buffer_size:
                    self.sliding_window.pop(0)

                # --- Detection (Only if Monitoring is Active) ---
                detections = []
                if self.monitoring_active:
                    detections = self.predict(frame) # LOCAL MODEL RE-ENABLED
                
                # --- Logic Engine ---
                detected_violation = None
                detected_conf = 0.0
                
                # Check for any malpractice class
                # 'Giving signal' removed as per user request (false positives)
                malpractice_classes = ['Using Phone', 'Giving object', 'Looking Friend', 'Looking Left', 'Looking Right']
                
                # Perform Head Pose Estimation using YOLO-Pose
                # Perform Head Pose Estimation using YOLO-Pose
                # (Logic moved to predict() to avoid double calculation)
                # But we still need 'gaze_direction' variable for the logic filter below
                gaze_direction = "Straight"
                for det in detections:
                    if det['type'] == 'pose':
                        gaze_direction = det['label']
                
                # --- CLOUD AI CHECK REMOVED ---
                # if self.monitoring_active and (time.time() - self.last_cloud_check > 5.0):
                #     self.last_cloud_check = time.time()
                #     threading.Thread(target=self._run_cloud_check, args=(frame.copy(),)).start()

                # --- MERGE RESULTS REMOVED ---
                # if self.ai_result and self.ai_result != "Normal":
                #    ...
                
                
                # --- LOGIC FILTER (The "Brain") ---
                # This overrides raw YOLO output with physical constraints
                
                final_violation = None
                final_conf = 0.0
                
                for det in detections:
                    label = det['label']
                    conf = det['confidence']
                    
                    # 1. Reject "Looking Left/Right" labels if Head is Straight
                    # If YOLO says "Looking..." but YOLO-Pose says "Straight", we trust Pose.
                    # REMOVED 'Looking Friend' from this filter so it works more easily
                    if label in ['Looking Left', 'Looking Right']:
                         # If Pose Model is active and says Straight, filter out
                         if self.pose_model and gaze_direction == "Straight":
                             continue
                             
                    # 2. Relaxed "Using Phone" check.
                    if label == 'Using Phone' and conf < 0.35:
                        continue

                    if label in malpractice_classes:
                        # If multiple violations, prioritize the one with highest confidence
                        if conf > final_conf:
                            final_violation = label
                            final_conf = conf
                
                detected_violation = final_violation
                detected_conf = final_conf
                
                # State Machine
                if self.violation_state == 'IDLE':
                    if detected_violation:
                        self.violation_state = 'RECORDING'
                        self.current_violation_label = detected_violation
                        self.violation_student_id = self.current_student_name # Capture ID at start
                        self.current_max_confidence = detected_conf
                        self.recording_start_time = time.time()
                        self.violation_frame_buffer = list(self.sliding_window)
                        self.cooldown_frames = 0
                        print(f"Violation Started: {detected_violation}")

                elif self.violation_state == 'RECORDING':
                    self.violation_frame_buffer.append(frame.copy())
                    if detected_violation:
                         self.cooldown_frames = 0
                         if detected_conf > self.current_max_confidence:
                             self.current_max_confidence = detected_conf
                    else:
                        self.cooldown_frames += 1
                    
                    elapsed = time.time() - self.recording_start_time
                    # Reduced cooldown from 10 to 3 frames for INSTANT alerting
                    if self.cooldown_frames > 3 or elapsed > 30.0:
                        print(f"Violation Ended. Saving clip...")
                        filename = self.save_incident_clip(self.current_violation_label, self.violation_frame_buffer)
                        if filename:
                            self.send_alert(self.current_violation_label, self.current_max_confidence, filename, self.violation_student_id)
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
                
                # --- Face Recognition & Attendance ---
                # Check Face Identity periodically
                student_name = self.recognize_face_in_frame(frame)
                
                # Display Student Name on top-right (REMOVED as per user request)
                # cv2.putText(frame, f"Student: {student_name}", (frame.shape[1] - 300, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                try:
                    # FULL SPEED: Send every frame (30 FPS)
                    # Using QVGA (320x240) allows this high speed over socket
                    small_frame = cv2.resize(frame, (320, 240)) 
                    _, buffer = cv2.imencode('.jpg', small_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                    b64_frame = base64.b64encode(buffer).decode('utf-8')
                    
                    if self.sio.connected:
                        self.sio.emit('video_frame', b64_frame)
                except:
                    pass

                # time.sleep(0.01) # Removed sleep to let processing run as fast as possible, flow control via frame skip



            else:
                # Camera NOT active
                if cap is not None:
                    cap.release()
                    cap = None
                    print("Camera Released (Waiting for Website).")
                
                # Sleep to prevent high CPU usage while idle
                time.sleep(0.5)






    def _run_cloud_check(self, frame):
        print("DEBUG: Starting Cloud Check Thread...") 
        res, conf = self.detect_with_gemini(frame)
        if res:
            print(f"DEBUG: Cloud Result -> {res}")
            self.ai_result = res
            self.ai_confidence = conf

if __name__ == "__main__":
    # Test run
    detector = MalpracticeDetector()
    detector.start_service()


