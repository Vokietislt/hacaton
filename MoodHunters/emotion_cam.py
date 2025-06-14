import cv2

import time
import csv
import os
from datetime import datetime
from deepface import DeepFace
import win32gui
import win32process
import psutil
import sqlite3
from dbfunctions import EmotionLogDB 

# ─── Configuration ────────────────────────────────────────────────────────────
CAMERA_INDEX = 0                  # Change to 1 or 2 if 0 doesn’t work
FRAME_WIDTH = 640                 # Resize width for performance
FRAME_HEIGHT = 480                # Resize height for performance
last_analyze_time = 0             # Store the last time analysis was done
ANALYZE_INTERVAL_SECONDS = 1      # Set interval to 1 second
frame_counter = 0
db = EmotionLogDB()
# ──────────────────────────────────────────────────────────────────────────────

# ─── Foreground App Detection ─────────────────────────────────────────────────
def get_foreground_app():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        exe_name = process.name()
        window_title = win32gui.GetWindowText(hwnd)
        return f"{exe_name} - {window_title}"
    except Exception:
        return "Unknown"
# ──────────────────────────────────────────────────────────────────────────────

# Initialize webcam with DirectShow backend (Windows)
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"Failed to open camera with index {CAMERA_INDEX}. Exiting.")
    exit(1)

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        break
    # Resize for performance
    frame_resized = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    # Inside the processing loop
    current_time = time.time()  # Get the current time in seconds
    # Analyze By seconds intervall
    if current_time - last_analyze_time > ANALYZE_INTERVAL_SECONDS: 
        last_analyze_time = current_time
        try:
            # DeepFace returns a list if multiple faces; otherwise a dict
            results = DeepFace.analyze(frame_resized, actions=["emotion"], enforce_detection=True)

            # Ensure results is iterable
            if not isinstance(results, list):
                results = [results]

            # Log and draw for each detected face
            for face_id, analysis in enumerate(results, start=1):
                region = analysis.get("region", {})
                x, y, w, h = region.get("x", 0), region.get("y", 0), region.get("w", 0), region.get("h", 0)

                if w == 0 or h == 0:
                    continue
                # Adjust region coords to original frame size if needed
                scale_x = frame.shape[1] / FRAME_WIDTH
                scale_y = frame.shape[0] / FRAME_HEIGHT
                x_orig = int(x * scale_x)
                y_orig = int(y * scale_y)
                w_orig = int(w * scale_x)
                h_orig = int(h * scale_y)
                dominant = analysis["dominant_emotion"]
                confidence = analysis["emotion"].get(dominant, 0.0)
                # Draw bounding box and label on original frame
                cv2.rectangle(frame, (x_orig, y_orig), (x_orig + w_orig, y_orig + h_orig), (0, 255, 0), 2)
                label = f"{dominant}: {confidence:.2f}"
                cv2.putText(
                    frame,
                    label,
                    (x_orig, y_orig - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                #ADD TO DATABASE
                timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
                foreground_app = get_foreground_app()
                db.insert_log(timestamp, face_id, dominant, confidence, foreground_app)
        except Exception:
            # If an error occurs (e.g., no face detected), skip this frame
            pass

    # Show the annotated frame
    cv2.imshow("DeepFace Emotion", frame)
    frame_counter += 1

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
# Clean up
db.close()
cap.release()
cv2.destroyAllWindows()
