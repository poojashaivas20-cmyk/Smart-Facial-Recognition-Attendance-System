import cv2
import numpy as np
import time
import os
from datetime import datetime
from flask import Flask
from database import db, Student, Attendance
from face_handler import FaceHandler
from config import Config

# 1. STANDALONE INITIALIZATION (Minimal Flask context for DB access)
scanner_app = Flask(__name__)
scanner_app.config.from_object(Config)
db.init_app(scanner_app)

# Initialize Face Handler
fh = FaceHandler()

# UI COLORS (B, G, R)
COLOR_PRIMARY = (235, 99, 37)     # Tech Blue
COLOR_SUCCESS = (10, 185, 129)    # Emerald Green
COLOR_DANGER = (68, 68, 239)      # Alert Red
COLOR_WHITE = (255, 255, 255)
COLOR_HEADER = (90, 40, 15)       # Dark Blue (B, G, R)
COLOR_BORDER = (180, 180, 180)    # Light Gray for outer border

# CANVAS DIMENSIONS
CAM_W, CAM_H = 1280, 720
HEADER_H = 100
CANVAS_W, CANVAS_H = CAM_W, CAM_H + HEADER_H

def setup_canvas(frame, status="SCANNING", match_info=None):
    # Create the base canvas (Dark background)
    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
    canvas[:] = (30, 30, 30) # Dark gray background

    # 1. DRAW HEADER
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, HEADER_H), COLOR_HEADER, -1)
    
    # Header Text: "Smart Attendance System"
    font = cv2.FONT_HERSHEY_DUPLEX
    text_title = "Smart Attendance System"
    text_size = cv2.getTextSize(text_title, font, 1.5, 3)[0]
    text_x = (CANVAS_W - text_size[0]) // 2
    cv2.putText(canvas, text_title, (text_x, 65), font, 1.5, COLOR_WHITE, 3, cv2.LINE_AA)

    # 2. DRAW BORDER AROUND CAMERA AREA
    # Color depends on status
    border_color = COLOR_SUCCESS if status == "MATCHED" else COLOR_PRIMARY
    cv2.rectangle(canvas, (0, HEADER_H), (CANVAS_W, CANVAS_H), border_color, 10)

    # 3. PLACE CAMERA FEED INTO CANVAS
    # (Ensure frame is CAM_W x CAM_H before placement)
    frame_resized = cv2.resize(frame, (CAM_W, CAM_H))
    canvas[HEADER_H:CANVAS_H, 0:CAM_W] = frame_resized

    return canvas

def draw_scanner_hud(frame, status="SCANNING", match_info=None):
    h, w = frame.shape[:2]
    
    # Scanning Zone Brackets (Centered in the camera feed)
    zone_w, zone_h = 350, 450
    start_x, start_y = (w - zone_w) // 2, (h - zone_h) // 2
    end_x, end_y = start_x + zone_w, start_y + zone_h
    
    color_zone = COLOR_PRIMARY if status == "SCANNING" else COLOR_SUCCESS
    t = 2
    L = 40
    # Brackets
    cv2.line(frame, (start_x, start_y), (start_x + L, start_y), color_zone, t*2)
    cv2.line(frame, (start_x, start_y), (start_x, start_y + L), color_zone, t*2)
    cv2.line(frame, (end_x, start_y), (end_x - L, start_y), color_zone, t*2)
    cv2.line(frame, (end_x, start_y), (end_x, start_y + L), color_zone, t*2)
    cv2.line(frame, (start_x, end_y), (start_x + L, end_y), color_zone, t*2)
    cv2.line(frame, (start_x, end_y), (start_x, end_y - L), color_zone, t*2)
    cv2.line(frame, (end_x, end_y), (end_x - L, end_y), color_zone, t*2)
    cv2.line(frame, (end_x, end_y), (end_x, end_y - L), color_zone, t*2)

    # Pulsing Scan Line
    line_y = start_y + int((zone_h / 2) * (1 + np.sin(time.time() * 3)))
    cv2.line(frame, (start_x + 10, line_y), (end_x - 10, line_y), color_zone, 2)
    
    # Overlay Info
    cv2.putText(frame, datetime.now().strftime("%I:%M:%S %p"), (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_WHITE, 2)
    
    if match_info:
        # Match Badge Background
        cv2.rectangle(frame, (start_x, end_y + 10), (end_x, end_y + 80), COLOR_SUCCESS, -1)
        # Match Text
        text = match_info[:15].upper()
        ts = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        tx = start_x + (zone_w - ts[0]) // 2
        cv2.putText(frame, text, (tx, end_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 1, COLOR_WHITE, 2)

    return (start_x, start_y, zone_w, zone_h)

def run_scanner():
    print("--- Starting Smart Attendance System Scanner ---")
    
    if not os.path.exists(fh.model_path):
        print(f"ERROR: Model not found at {fh.model_path}")
        return

    # Initialize Camera
    print("Opening camera...")
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("DirectShow failed/ignored. Trying default backend...")
            cap = cv2.VideoCapture(0)
    except Exception as e:
        print(f"Camera Open Exception: {e}")
        return
        
    if not cap.isOpened():
        print("CRITICAL: Camera detection failed. No working camera found.")
        return
        
    print("Camera successfully opened.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

    cooldown = {} 
    match_display_timer = 0
    match_display_name = ""

    print("Scanner System Active. Press 'q' to exit.")

    print("Starting display loop. Look for a window titled 'Smart Attendance System'.")
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret: 
            print("ERROR: Failed to read frame from camera.")
            break

        frame = cv2.flip(frame, 1) # Mirror view
        status = "SCANNING" if match_display_timer < time.time() else "MATCHED"
        
        # 1. DRAW SCANNER HUD (Inside camera frame)
        zx, zy, zw, zh = draw_scanner_hud(frame, status, match_display_name if status == "MATCHED" else None)
        
        # 2. ENCAPSULATE FRAME IN PROFESSIONAL CANVAS (Header + Border)
        canvas = setup_canvas(frame, status)
        
        if status == "SCANNING":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fh.face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                # Recognition logic only if face is in centered zone
                if x > zx and x + w < zx + zw and y > zy and y + h < zy + zh:
                    is_live, msg = fh.is_liveness_valid(frame, x, y, w, h)
                    if not is_live: continue

                    # Recognize
                    try:
                        face_img = gray[y:y+h, x:x+w]
                        face_img = cv2.resize(face_img, (200, 200))
                        sid, conf = fh.recognizer.predict(face_img)
                        print(f"Face Detected - ID: {sid}, Conf: {conf:.2f}")

                        if conf < 75:
                            with scanner_app.app_context():
                                student = Student.query.get(sid)
                                if student:
                                    print(f"Match Confirmed: {student.name}")
                                    now = time.time()
                                    if sid not in cooldown or (now - cooldown[sid] > 10):
                                        # Mark DB
                                        try:
                                            today = datetime.utcnow().date()
                                            existing = Attendance.query.filter(
                                                Attendance.student_id == sid, 
                                                db.func.date(Attendance.check_in_time) == today
                                            ).first()
                                            
                                            if not existing:
                                                new_log = Attendance(student_id=sid)
                                                db.session.add(new_log)
                                                db.session.commit()
                                                print(f"SUCCESS: Attendance logged for {student.name}")
                                            else:
                                                print(f"INFO: {student.name} already marked for today.")
                                                
                                            cooldown[sid] = now
                                            match_display_name = student.name
                                            match_display_timer = time.time() + 3
                                        except Exception as db_err:
                                            print(f"DATABASE ERROR: {db_err}")
                    except Exception as rec_err:
                        print(f"RECOGNITION ERROR: {rec_err}")

        if frame_count % 60 == 0:
            print("Processing camera frames... (Window should be visible)")
        frame_count += 1

        cv2.namedWindow('Smart Attendance System', cv2.WINDOW_AUTOSIZE)
        try:
            cv2.setWindowProperty('Smart Attendance System', cv2.WND_PROP_TOPMOST, 1)
        except:
            pass
            
        cv2.imshow('Smart Attendance System', canvas)
        
        # Check for 'q' key or if the window was closed via the 'X' button
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
            
        try:
            if cv2.getWindowProperty('Smart Attendance System', cv2.WND_PROP_VISIBLE) < 1:
                break
        except:
            # Fallback if property check fails
            pass

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        run_scanner()
    except Exception as e:
        import traceback
        print("A FATAL ERROR OCCURRED:")
        traceback.print_exc()
