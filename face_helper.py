import face_recognition
import cv2
import os
import numpy as np
import pickle

class FaceRecognizer:
    def __init__(self, known_faces_dir='known_faces', encoding_cache='database/encodings.pkl'):
        self.known_encodings = []
        self.known_names = []
        self.encoding_cache = encoding_cache
        self.load_known_faces(known_faces_dir)

    def load_known_faces(self, known_faces_dir):
        if not os.path.exists(known_faces_dir):
            os.makedirs(known_faces_dir, exist_ok=True)
            print("⚠️ ไม่พบโฟลเดอร์ known_faces — ระบบจะไม่จำหน้าใคร")
            return

        if os.path.exists(self.encoding_cache):
            print("✅ โหลด face encodings จาก cache")
            with open(self.encoding_cache, 'rb') as f:
                data = pickle.load(f)
                self.known_encodings = data['encodings']
                self.known_names = data['names']
            return

        print("🔄 กำลังเรียนรู้ใบหน้า...")
        for person_name in os.listdir(known_faces_dir):
            person_dir = os.path.join(known_faces_dir, person_name)
            if not os.path.isdir(person_dir):
                continue
            for img_file in os.listdir(person_dir):
                img_path = os.path.join(person_dir, img_file)
                try:
                    img = face_recognition.load_image_file(img_path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        self.known_encodings.append(encodings[0])
                        self.known_names.append(person_name)
                        print(f"  ✅ เรียนรู้: {person_name} ({img_file})")
                except Exception as e:
                    print(f"  ❌ ข้าม {img_file}: {e}")

        os.makedirs(os.path.dirname(self.encoding_cache), exist_ok=True)
        with open(self.encoding_cache, 'wb') as f:
            pickle.dump({'encodings': self.known_encodings, 'names': self.known_names}, f)
        print(f"✅ จำได้ {len(set(self.known_names))} คน")

    def recognize(self, frame, scale=0.25):
        small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        names = []
        for enc in encodings:
            if self.known_encodings:
                matches = face_recognition.compare_faces(self.known_encodings, enc, tolerance=0.5)
                distances = face_recognition.face_distance(self.known_encodings, enc)
                best = np.argmin(distances)
                name = self.known_names[best] if matches[best] else "Unknown"
            else:
                name = "Unknown"
            names.append(name)
        factor = int(1 / scale)
        locations = [(t*factor, r*factor, b*factor, l*factor) for t, r, b, l in locations]
        return locations, names

    def get_nearest_name(self, cx, cy, face_locations, face_names):
        if not face_locations:
            return "Unknown"
        min_dist = float('inf')
        nearest = "Unknown"
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            face_cx = (left + right) // 2
            face_cy = (top + bottom) // 2
            dist = ((cx - face_cx)**2 + (cy - face_cy)**2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest = name
        return nearest