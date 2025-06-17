import os
import sys
import asyncio

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import and run the worker
from gpu_worker import GPUWorker

if __name__ == "__main__":
    worker = GPUWorker()
    asyncio.run(worker.run())
