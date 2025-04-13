import os
from flask import Flask, request, jsonify, send_file
from ultralytics import YOLO
from PIL import Image, ImageDraw
import io

app = Flask(__name__)

# Load YOLO model
model = None


def draw_boxes(image, detections):
    draw = ImageDraw.Draw(image)
    for detection in detections:
        box = detection["box"]
        confidence = detection["confidence"]
        class_name = detection["class_name"]

        # Draw rectangle
        draw.rectangle(box, outline="red", width=2)

        # Draw label
        label = f"{class_name} {confidence:.2f}"
        draw.text((box[0], box[1] - 10), label, fill="red")

    return image


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


@app.route("/load_model", methods=["POST"])
def load_model():
    global model

    data = request.get_json()
    model_name = data.get("model_name", "yolov11n.pt")

    try:
        model = YOLO(model_name)
        return jsonify(
            {"status": "success", "message": f"Model {model_name} loaded successfully"}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/detect", methods=["POST"])
def detect_objects():
    global model

    if model is None:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "No model loaded. Call /load_model first",
                }
            ),
            400,
        )

    if "image" not in request.files:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    try:
        # Get image from request
        file = request.files["image"]
        img = Image.open(file.stream)

        # Run inference
        results = model(img)

        # Process results
        result_data = []
        for result in results:
            boxes = result.boxes.cpu().numpy()
            for i, box in enumerate(boxes):
                result_data.append(
                    {
                        "box": box.xyxy[0].tolist(),
                        "confidence": float(box.conf[0]),
                        "class": int(box.cls[0]),
                        "class_name": result.names[int(box.cls[0])],
                    }
                )
        # Draw boxes on image
        annotated_img = draw_boxes(img.copy(), result_data)

        # Save image to bytes
        img_byte_arr = io.BytesIO()
        annotated_img.save(img_byte_arr, format="JPEG")
        img_byte_arr.seek(0)

        # Return both the detections and the image
        return send_file(
            img_byte_arr,
            mimetype="image/jpeg",
            as_attachment=True,
            download_name="annotated_image.jpg",
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
