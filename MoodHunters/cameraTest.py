import time
import cv2
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot access camera")
    exit()
while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Test", frame)
    
   # time.sleep(1)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap.release()
cv2.destroyAllWindows()
