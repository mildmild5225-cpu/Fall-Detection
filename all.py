from ultralytics import YOLO, solutions
import cv2
import math
from function.helper import extract_detections, create_mask
from function.helper_email import send_email
from function.face_helper import FaceRecognizer
from database.db import init_db, save_fall_event
import numpy as np
import time
import threading
import platform
import os
from datetime import datetime

def get_device():
    import torch
    if platform.system() == "Darwin":
        if torch.backends.mps.is_available():
            return 'mps'
    return 'cpu'

def detect_from_video(video_path, confiden=0.5, use_camera=False):
    device = get_device()
    print(f"Using device: {device}")

    # เปิดกล้องวงจรปิด หรือวิดีโอ
    if use_camera:
        cap = cv2.VideoCapture(0)  # 0 = กล้องหลัก, เปลี่ยนเป็น RTSP URL สำหรับ IP Camera
        # ตัวอย่าง RTSP: cap = cv2.VideoCapture("rtsp://username:password@192.168.1.100:554/stream")
    else:
        cap = cv2.VideoCapture(video_path)

    model = YOLO('model/yolo11n.pt').to(device)
    face_recognizer = FaceRecognizer(known_faces_dir='known_faces')

    init_db()

    cv2.namedWindow("FALL DETECTION SYSTEM", cv2.WINDOW_NORMAL)

    region_points = np.array([[40, 11], [1863, 7], [1870, 1074], [46, 1066]])

    counter = solutions.ObjectCounter(
        reg_pts=region_points.tolist(),
        names=model.names,
        draw_tracks=False,
        line_thickness=2,
        view_in_counts=False,
        view_out_counts=False,
    )

    alert_interval = 5
    last_alert_time = 0
    fall_threshold_ratio = 1.2
    # เพิ่มก่อน while loop
    name_cache = {}  # เก็บชื่อตาม track id

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
             break

        current_time = time.time()
        time_remaining = max(0, int(alert_interval - (current_time - last_alert_time)))

        masked_frame = create_mask(frame, region_points)
        track = model.track(masked_frame, persist=True, show=False,
                        verbose=False, conf=confiden, device=device, classes=[0])

        img = counter.start_counting(frame, track)
        result_data = extract_detections(track, model)

    # Face recognition
        face_locations, face_names = face_recognizer.recognize(frame)

        for values in result_data:
            clsname = values['classname']
            cx, cy = values['center']
            x1, y1, x2, y2 = values['box']
            width = x2 - x1
            height = y2 - y1
            track_id = values.get('track_id', 0)

            if clsname == "person":
                ratio = width / height

            # หาชื่อจาก face recognition
            detected_name = face_recognizer.get_nearest_name(cx, cy, face_locations, face_names)

            # ถ้าจำได้ → อัพเดท cache
            if detected_name != "Unknown":
                name_cache[track_id] = detected_name
            
            # ใช้ชื่อจาก cache ถ้ามี
            person_name = name_cache.get(track_id, "Unknown")

            # วาดชื่อ
            color = (0, 255, 0) if person_name != "Unknown" else (128, 128, 128)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, person_name, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if ratio > fall_threshold_ratio:
                if current_time - last_alert_time > alert_interval:
                    label = f"FALL: {person_name}"
                    cv2.putText(img, label, (x1, y1 - 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    os.makedirs("result", exist_ok=True)
                    image_path = f"result/fall_{person_name}_{timestamp}.jpg"
                    cv2.imwrite(image_path, img)
                    cv2.imshow("⚠️ FALL DETECTED!", img)
                    cv2.waitKey(1)

                    save_fall_event(
                        person_name=person_name,
                        image_path=image_path,
                        location=f"{cx},{cy}",
                        timestamp=datetime.now().isoformat()
                    )

                    print(f"!!!! FALL DETECTED: {person_name} at ({cx}, {cy}) !!!!")
                    threading.Thread(
                        target=send_email,
                        args=(f"CCTV FALL ALERT - {person_name}",
                              f"ตรวจพบการหกล้มของ {person_name}", image_path)
                    ).start()
                    last_alert_time = current_time

        print(f"Time to next alert: {time_remaining}s", end="\r")
        cv2.imshow('FALL DETECTION SYSTEM', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
             break

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("video error / end of stream")
            break

        current_time = time.time()
        time_remaining = max(0, int(alert_interval - (current_time - last_alert_time)))

        masked_frame = create_mask(frame, region_points)
        track = model.track(masked_frame, persist=True, show=False,
                            verbose=False, conf=confiden, device=device, classes=[0])

        img = counter.start_counting(frame, track)
        result_data = extract_detections(track, model)

        # Face recognition บน frame ทั้งหมด
        face_locations, face_names = face_recognizer.recognize(frame)
        if face_names:
          print(f"พบใบหน้า: {face_names}")

        # วาดชื่อบุคคล
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            color = (0, 255, 0) if name != "Unknown" else (128, 128, 128)
            cv2.rectangle(img, (left, top), (right, bottom), color, 2)
            cv2.putText(img, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        for values in result_data:
            clsname = values['classname']
            cx, cy = values['center']
            x1, y1, x2, y2 = values['box']
            width = x2 - x1
            height = y2 - y1

            if clsname == "person":
                ratio = width / height
                ground_node_y = y2
                frame_height  = frame.shape[0]
                ground_ratio  = ground_node_y / frame_height

                angle = math.degrees(math.atan2(height, width))

                cv2.putText(img, f"Ratio: {ratio:.2f}", (x1, y1-50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                cv2.putText(img, f"Angle: {angle:.1f}", (x1, y1-35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)
                cv2.putText(img, f"Ground: {ground_ratio:.2f}", (x1, y1-20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)


                # หาชื่อบุคคลที่ใกล้ที่สุดกับ bounding box
                person_name = face_recognizer.get_nearest_name(
                    cx, cy, face_locations, face_names
                )

                is_horizontal = ratio > 0.9
                is_grounded   = ground_ratio > 0.3
                is_tilted     = angle < 45

                if is_horizontal and is_grounded and is_tilted:
                    if current_time - last_alert_time > alert_interval:
                        # วาด FALL DETECTED
                        label = f"FALL: {person_name}"
                        cv2.putText(img, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)

                        # บันทึกรูป
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        os.makedirs("result", exist_ok=True)
                        image_path = f"result/fall_{person_name}_{timestamp}.jpg"
                        cv2.imwrite(image_path, img)

                        # โชว์รูปทันที
                        cv2.imshow("⚠️ FALL DETECTED!", img)
                        cv2.waitKey(1)

                        # บันทึกลง database
                        save_fall_event(
                            person_name=person_name,
                            image_path=image_path,
                            location=f"{cx},{cy}",
                            timestamp=datetime.now().isoformat()
                        )

                        print(f"!!!! FALL DETECTED: {person_name} at ({cx}, {cy}) !!!!")
                        print(f"✅ บันทึกรูปที่: {image_path}")

                        # ส่งอีเมล
                        threading.Thread(
                            target=send_email,
                            args=(
                                f"CCTV FALL ALERT - {person_name}",
                                f"ตรวจพบการหกล้มของ {person_name}",
                                image_path
                            )
                        ).start()

                        last_alert_time = current_time

        print(f"Time to next alert: {time_remaining}s", end="\r")
        cv2.imshow('FALL DETECTION SYSTEM', img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # ใช้วิดีโอ
    detect_from_video("video/fall2.mp4", confiden=0.3)

    # ใช้กล้องวงจรปิด
    # detect_from_video("", confiden=0.3, use_camera=True)
