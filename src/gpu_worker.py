import os
import time
import json
import base64
import redis
from PIL import Image
import io
from ultralytics import YOLO
from pathlib import Path

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_QUEUE = "detection_jobs"

# Model configuration
MODELS_DIR = Path("models")
DEFAULT_MODEL = "yolov8n"

class GPUWorker:
    def __init__(self):
        self.redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.model = self.load_model()

    def load_model(self):
        """Load the YOLO model"""
        model_path = MODELS_DIR / f"{DEFAULT_MODEL}.pt"
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")
        return YOLO(str(model_path))

    def process_image(self, image_data):
        """Process an image using the loaded model"""
        # Convert base64 to image
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes))

        # Run inference
        results = self.model(img)
        
        # Process results
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detections.append({
                    "class": cls,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })

        return detections

    def run(self):
        """Main worker loop"""
        print("GPU Worker started. Waiting for jobs...")
        
        while True:
            try:
                # Get job from queue (blocking)
                job_data = self.redis_conn.brpop(REDIS_QUEUE, timeout=0)
                
                if job_data:
                    # job_data is a tuple (queue_name, job_json)
                    job_json = job_data[1]
                    job = json.loads(job_json)
                    
                    print(f"Processing job for user {job['user_id']}")
                    
                    # Process the image
                    detections = self.process_image(job['image'])
                    
                    # TODO: Handle the results (store in database, notify client, etc.)
                    print(f"Processed image with {len(detections)} detections")
                    
            except Exception as e:
                print(f"Error processing job: {e}")
                time.sleep(1)  # Prevent tight loop on errors

if __name__ == "__main__":
    worker = GPUWorker()
    worker.run() 