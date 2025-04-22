import cv2
import numpy as np
import time
# Start video capture
cap = cv2.VideoCapture(0)

# Read the first frame and prepare it
ret, frame1 = cap.read()
gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)


black_screen = np.zeros((480, 640, 3), dtype=np.uint8)  # height x width x channels (BGR)

# Movement threshold: how many pixels need to change to count as movement
STREAMING = False

MOVEMENT_THRESHOLD =30000#15000  #trigger vision push

STREAMING_COOLDOWN_TIME = 1  # seconds to wait
DETECTION_COOLDOWN_TIME = 0.5  # seconds to wait
STREAMING_PT = 0
DETECTION_PT = 0

CURRENT_TIME = 0  # Initialize current time

while True:
    ret, frame2 = cap.read()
    CURRENT_TIME = time.time()
    if not ret:
        break

    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)

    # Compute difference and threshold
    delta = cv2.absdiff(gray1, gray2)
    thresh = cv2.threshold(delta, 5, 255, cv2.THRESH_BINARY)[1]

    # Count non-zero pixels (i.e., areas with motion)
    motion_score = np.count_nonzero(thresh)

    if motion_score > MOVEMENT_THRESHOLD:
        print("Movement detected!")
        STREAMING = True
        STREAMING_PT = CURRENT_TIME    

    if STREAMING :
        CURRENT_TIME = time.time()
        print("Streaming...")
        display_frame = frame2.copy()
        if CURRENT_TIME - STREAMING_PT > STREAMING_COOLDOWN_TIME:
            STREAMING = False
            display_frame = black_screen.copy()

        cv2.imshow("Black Screen", display_frame)
        

            

    # Update previous frame
    gray1 = gray2.copy()

    # Exit loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release camera and close windows
cap.release()
cv2.destroyAllWindows()
