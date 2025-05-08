import os
from pathlib import Path
from typing import Dict, List, Optional

from ultralytics import YOLO

# Configuration
MODELS_DIR = Path("models")
SUPPORTED_MODELS = {
    "yolov8n": {
        "file_name": "yolov8n.pt",
        "description": "YOLOv8 Nano - smallest and fastest model",
    },
}

DEFAULT_MODEL = "yolov8n"

# Ensure models directory exists
os.makedirs(MODELS_DIR, exist_ok=True)


class ModelManager:
    _instance = None
    _loaded_model = None
    _current_model_name = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance

    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get the path to a model file by name"""
        if model_name not in SUPPORTED_MODELS:
            return None

        model_path = MODELS_DIR / SUPPORTED_MODELS[model_name]["file_name"]
        if not model_path.exists():
            return None

        return model_path

    def load_model(self, model_name: str) -> Optional[YOLO]:
        """Load a model by name"""
        model_path = self.get_model_path(model_name)
        if not model_path:
            return None

        try:
            self._loaded_model = YOLO(str(model_path))
            self._current_model_name = model_name
            return self._loaded_model
        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
            return None

    def get_current_model(self) -> tuple:
        """Get the currently loaded model"""
        return self._loaded_model, self._current_model_name
