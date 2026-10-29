
import platform
import os
import torch
import ultralytics

print("===== PCB-AI-Inspector Hardware Check =====")
print("Operating system:", platform.system())
print("Python:", platform.python_version())
print("CPU cores available:", os.cpu_count())
print("PyTorch:", torch.__version__)
print("Ultralytics:", ultralytics.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("GPU: No CUDA GPU available to PyTorch")
    print("Training can still run on CPU, but may be slower.")
