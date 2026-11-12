import json
import requests
from ultralytics import YOLO
from PIL import Image

AUTH = ("thinh_txt", "admin12345")
BASE_URL = "http://localhost:8080/api"
JOB_ID = 12

# COCO 17 keypoint names
COCO_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

# Fetch label specs
r = requests.get(f"{BASE_URL}/labels?job_id={JOB_ID}", auth=AUTH)
r.raise_for_status()
labels = r.json()["results"]
person_label = next(l for l in labels if l["name"] == "person")
sublabel_map = {sl["name"]: sl["id"] for sl in person_label["sublabels"]}

# Fetch meta
r = requests.get(f"{BASE_URL}/jobs/{JOB_ID}/data/meta", auth=AUTH)
r.raise_for_status()
meta = r.json()
frames = meta["frames"]

model = YOLO("D:/0- MY WORK/6- TS UTEHY 2026/cvat/yolov8m-pose.pt")

shapes = []
for frame_idx, frame_info in enumerate(frames):
    img_name = frame_info["name"]
    img_path = f"D:/3. AI THUC CHIEN/4- DAY 04/K5-L2B-DAY04-BUI-VAN-THINH-2A202604040-KeypointPose-Student-main/data/persons-extra/{img_name}"
    im = Image.open(img_path)
    w, h = im.size
    
    results = model(im, verbose=False)[0]
    
    for box, kpts in zip(results.boxes, results.keypoints):
        xyxy = box.xyxy[0].tolist()
        box_h = xyxy[3] - xyxy[1]
        conf = float(box.conf[0])
        if box_h < 60 or conf < 0.4:
            continue
            
        kp_data = kpts.data[0].tolist() # (17, 3) -> x, y, conf
        
        elements = []
        for i, name in enumerate(COCO_NAMES):
            kx, ky, kc = kp_data[i]
            # outside boundary check
            is_outside = kx < 0 or kx >= w or ky < 0 or ky >= h
            is_occluded = (kc < 0.5 and not is_outside)
            
            elements.append({
                "type": "points",
                "label_id": sublabel_map[name],
                "points": [round(kx, 2), round(ky, 2)],
                "occluded": is_occluded,
                "outside": is_outside,
                "frame": frame_idx
            })
            
        shapes.append({
            "type": "skeleton",
            "label_id": person_label["id"],
            "frame": frame_idx,
            "elements": elements
        })

print(f"Total skeleton shapes to upload: {len(shapes)}")

# Upload to CVAT
payload = {
    "shapes": shapes,
    "tracks": [],
    "tags": [],
    "version": 0
}
r = requests.patch(f"{BASE_URL}/jobs/{JOB_ID}/annotations?action=create", json=payload, auth=AUTH)
r.raise_for_status()
print("Uploaded persons-extra annotations successfully!")

