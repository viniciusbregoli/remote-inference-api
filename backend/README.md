# YOLO Object Detection API

A FastAPI-based REST API for object detection using YOLOv8 models.

## Features

- Object detection using YOLOv8 models
- Support for different YOLOv8 model sizes (n, s, m, l, x)
- Automatic API documentation
- Health check endpoint
- Image annotation with bounding boxes and labels

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

2. Access the API documentation at `http://localhost:5000/docs`

## API Endpoints

### Health Check
- **GET** `/health`
- Returns the health status of the API

### Load Model
- **POST** `/load_model`
- Request body:
```json
{
    "model_name": "yolov8n.pt"
}
```
- Loads a YOLOv8 model for object detection

### Detect Objects
- **POST** `/detect`
- Upload an image file
- Returns an annotated image with detected objects

## Example Usage

1. Load a model:
```bash
curl -X POST "http://localhost:5000/load_model" \
     -H "Content-Type: application/json" \
     -d '{"model_name": "yolov8n.pt"}'
```

2. Detect objects in an image:
```bash
curl -X POST "http://localhost:5000/detect" \
     -F "image=@path/to/your/image.jpg"
```

## Environment Variables

- `PORT`: Server port (default: 5000)

## License

MIT