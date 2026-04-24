import cv2
import numpy as np
import os

class FaceHandler:
    def __init__(self):
        # Initialize OpenCV Haar Cascade for Face & Eye Detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Initialize OpenCV Face Recognizer (LBPH)
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.model_path = "static/faces/trainer.yml"
        
        if os.path.exists(self.model_path):
            self.recognizer.read(self.model_path)

    def is_liveness_valid(self, frame, x, y, w, h):
        """
        Calibrated anti-proxy checks for low-light/night conditions:
        1. Texture analysis (Laplacian variance) - lower threshold for grainy cams.
        2. Feature visualization - applying CLAHE to normalize brightness.
        3. Feature verification - relaxed eye detection for shadows.
        """
        roi_color = frame[y:y+h, x:x+w]
        roi_gray = cv2.cvtColor(roi_color, cv2.COLOR_BGR2GRAY)
        
        # --- PREPROCESSING FOR LOW LIGHT ---
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # This makes features (like eyes) much more visible in the dark.
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        roi_norm = clahe.apply(roi_gray)
        
        # 1. Laplacian Variance Check
        # Lowered floor from 35 -> 25 to accommodate grainy laptop cam sensors at night.
        # Increased ceiling from 800 -> 1200 to prevent false pattern triggers by ISO noise.
        variance = cv2.Laplacian(roi_gray, cv2.CV_64F).var()
        
        if variance < 25: 
            return False, "Low Clarity: Please turn on a light or clean your camera lens."
        
        if variance > 1500: 
            return False, "Digital Noise Detected: Too dark for reliable scanning."
        
        # 2. Eye Detection on Normalized ROI
        # Reduced minNeighbors from 4 -> 3 for better detection in low contrast/shadows.
        eyes = self.eye_cascade.detectMultiScale(roi_norm, scaleFactor=1.1, minNeighbors=3)
        if len(eyes) < 1: 
            return False, "Eyes Not Detected: Please look directly at the camera."
            
        return True, "Liveness Success"

    def extract_face(self, frame):
        """
        Detects and crops the face.
        Returns (face_img, error_msg)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        
        if len(faces) == 0:
            return None, "Face Not Detected: Ensure your entire face is visible."
        
        (x, y, w, h) = faces[0]
        
        # Perform liveness check during registration
        is_live, msg = self.is_liveness_valid(frame, x, y, w, h)
        if not is_live:
            return None, msg # Return the specific reason for failure
            
        face_img = gray[y:y+h, x:x+w]
        return cv2.resize(face_img, (200, 200)), None

    def train_recognizer(self, student_faces, student_ids):
        """Trains the LBPH recognizer with student faces and IDs."""
        if not student_faces:
            return False
            
        self.recognizer.train(student_faces, np.array(student_ids))
        self.recognizer.save(self.model_path)
        return True

    def recognize_face(self, frame):
        """
        Detects faces, performs liveness check, and predicts IDs.
        Returns a list of tuples: (id, is_live, status_msg)
        """
        if not os.path.exists(self.model_path):
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        
        results = []
        for (x, y, w, h) in faces:
            is_live, msg = self.is_liveness_valid(frame, x, y, w, h)
            
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))
            
            id_, confidence = self.recognizer.predict(face_img)
            
            # In LBPH, lower confidence scores mean the match is BETTER (distance is smaller).
            # Threshold 55.0 is much stricter than 80.0, reducing false positives.
            if confidence < 55.0:
                results.append((id_, is_live, msg))
            else:
                print(f"INFO: Detected ID {id_} but confidence {confidence:.2f} was too high (Uncertain)")
                    
        return results
