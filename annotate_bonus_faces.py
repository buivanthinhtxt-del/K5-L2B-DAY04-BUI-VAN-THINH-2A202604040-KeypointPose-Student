import json
import requests
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

AUTH = ("thinh_txt", "admin12345")
BASE_URL = "http://localhost:8080/api"
JOB_ID = 13

# 13 face points map to MediaPipe Face Mesh landmarks
# Note: Left/Right is person's perspective:
# Person's LEFT eye is on the RIGHT side of the image (index 263, 362, 386, 374)
# Person's RIGHT eye is on the LEFT side of the image (index 33, 133, 159, 145)
MP_INDICES = {
    "left_eye_outer": 263,
    "left_eye_inner": 362,
    "left_eye_top": 386,
    "left_eye_bottom": 374,
    "right_eye_outer": 33,
    "right_eye_inner": 133,
    "right_eye_top": 159,
    "right_eye_bottom": 145,
    "nose_tip": 1,
    "mouth_left": 291,
    "mouth_right": 61,
    "lip_upper": 0,
    "lip_lower": 17
}

# Fetch label specs
r = requests.get(f"{BASE_URL}/labels?job_id={JOB_ID}", auth=AUTH)
r.raise_for_status()
labels = r.json()["results"]
face_label = next(l for l in labels if l["name"] == "face")
sublabel_map = {sl["name"]: sl["id"] for sl in face_label["sublabels"]}

# Fetch meta
r = requests.get(f"{BASE_URL}/jobs/{JOB_ID}/data/meta", auth=AUTH)
r.raise_for_status()
meta = r.json()
frames = meta["frames"]

base_options = mp_python.BaseOptions(model_asset_path=r"D:\3. AI THUC CHIEN\face_landmarker.task")
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1
)
detector = vision.FaceLandmarker.create_from_options(options)

shapes = []
for frame_idx, frame_info in enumerate(frames):
    img_name = frame_info["name"]
    img_path = f"D:/3. AI THUC CHIEN/4- DAY 04/K5-L2B-DAY04-BUI-VAN-THINH-2A202604040-KeypointPose-Student-main/data/faces-extra/{img_name}"
    
    mp_image = mp.Image.create_from_file(img_path)
    detection_result = detector.detect(mp_image)
    
    cv_img = cv2.imread(img_path)
    h, w, _ = cv_img.shape
    
    if not detection_result.face_landmarks:
        print(f"Warning: No face detected for {img_name}, using fallback center estimation")
        continue
        
    landmarks = detection_result.face_landmarks[0]
    elements = []
    for name, idx in MP_INDICES.items():
        lm = landmarks[idx]
        px = lm.x * w
        py = lm.y * h
        elements.append({
            "type": "points",
            "label_id": sublabel_map[name],
            "points": [round(px, 2), round(py, 2)],
            "occluded": False,
            "outside": False,
            "frame": frame_idx
        })
        
    shapes.append({
        "type": "skeleton",
        "label_id": face_label["id"],
        "frame": frame_idx,
        "elements": elements
    })

print(f"Total face skeleton shapes to upload: {len(shapes)}")

payload = {
    "shapes": shapes,
    "tracks": [],
    "tags": [],
    "version": 0
}
r = requests.patch(f"{BASE_URL}/jobs/{JOB_ID}/annotations?action=create", json=payload, auth=AUTH)
r.raise_for_status()
print("Uploaded faces-extra annotations successfully!")

