# use this file exactly you dumb idiot
import cv2

import engine

ew = engine.GStreamerEngineWriter(
    video_size=(320, 240, 30), socket_path="engineering", repeat_frames=True
)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_FPS, 30)

try:
    print("starting up")
    ret, frame = cap.read()
    while cap.isOpened():
        ew.write_frame(frame)
        ret, frame = cap.read()
except KeyboardInterrupt:
    print("ctrl-c")
    cap.release()
