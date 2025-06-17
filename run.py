import os
import sys

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import and run the app
from app import app
import uvicorn

if __name__ == "__main__":
    # Default to port 5000
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port) 