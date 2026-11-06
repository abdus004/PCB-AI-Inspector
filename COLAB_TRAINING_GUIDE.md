# Google Colab T4 Training Guide: Experiments 1 & 2

This guide provides the complete, self-contained workflow for running controlled experiments on a **Google Colab Tesla T4 GPU**.

> [!IMPORTANT]
> **Safety Rules Followed**:
> - Does **not** modify or overwrite local files, datasets, or weights.
> - Preserves the original `models/best.pt` (the 30-epoch training checkpoint).
> - Saves each experiment to its own dedicated output directory (`exp1_finetune_best`, `exp2_controlled_finetune`).
> - `exist_ok=False` ensures existing experiment outputs are never overwritten.

---

## 1. Prerequisites (Files to Upload to Colab or Google Drive)

From your local machine `c:\Users\Dell\Documents\PCB-AI-Inspector`:
1. **`models/best.pt`** (5.5 MB) — Your original trained weights from the 30-epoch training run.
2. **`datasets/pcb-yolo-final.zip`** (1.18 GB) — The full dataset archive already present in your project.
3. **`train_colab_exp2.py`** — The Experiment 2 controlled training script.

---

## 2. Step-by-Step Colab Notebook Cells

Open a notebook at [colab.research.google.com](https://colab.research.google.com).
Go to **Runtime** → **Change runtime type** → select **T4 GPU** → **Save**.

### Cell 1: Verify GPU Acceleration
```python
import torch
print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device Name:", torch.cuda.get_device_name(0))
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
else:
    print("ERROR: GPU not enabled! Please select T4 GPU under Runtime settings.")
```

### Cell 2: Install Ultralytics
```bash
!pip install --upgrade ultralytics
```

### Cell 3: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
```

### Cell 4: Unzip Dataset to Local NVMe Storage
```bash
# Unzip to fast local Colab SSD (do not train directly on Drive storage)
!unzip -q /content/drive/MyDrive/pcb-yolo-final.zip -d /content/pcb-yolo-final
```

### Cell 5: Create Dataset Config (`/content/pcb_colab.yaml`)
```python
yaml_content = """
path: /content/pcb-yolo-final

train: images/train
val: images/val
test: images/test

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
"""

with open("/content/pcb_colab.yaml", "w") as f:
    f.write(yaml_content.strip())

print("Dataset config written to /content/pcb_colab.yaml")
```

---

## 3. Execute Experiment 2: Controlled Fine-Tuning

### Cell 6: Run `train_colab_exp2.py`
```bash
!python /content/drive/MyDrive/train_colab_exp2.py \
  --weights /content/drive/MyDrive/best.pt \
  --data /content/pcb_colab.yaml \
  --epochs 20 \
  --batch 16 \
  --lr0 0.0003 \
  --patience 8 \
  --project /content/runs/experiments \
  --name exp2_controlled_finetune
```

*(Expected runtime on T4 GPU: ~1.5 minutes per epoch; ~20–30 minutes total. Early stopping patience=8 triggers if validation fitness plateaus.)*

### Cell 7: Backup Experiment 2 Checkpoints to Google Drive
```bash
# Save outputs to Google Drive
!cp /content/runs/experiments/exp2_controlled_finetune/weights/best.pt /content/drive/MyDrive/exp2_best.pt
!cp /content/runs/experiments/exp2_controlled_finetune/results.csv /content/drive/MyDrive/exp2_results.csv
!cp /content/runs/experiments/exp2_controlled_finetune/confusion_matrix.png /content/drive/MyDrive/exp2_confusion_matrix.png

print("Experiment 2 results backed up to Google Drive successfully!")
```

---

## 4. Experiment 2 vs. Baseline Comparison Targets (Validation Set)

| Metric | Original Model Baseline (`models/best.pt`) | Experiment 1 (Reference) | Experiment 2 Target |
|---|---:|---:|---:|
| **Overall Precision** | 91.5% | 86.0% | $\ge \mathbf{88.5\%}$ |
| **Overall Recall** | 90.2% | 93.1% | $\ge \mathbf{91.0\%}$ |
| **Overall mAP@50** | 92.0% | 93.2% | $\ge \mathbf{93.5\%}$ |
| **Overall mAP@50-95** | 45.4% | 44.2% | $\ge \mathbf{45.5\%}$ |
| **Short Precision** | 86.6% | **47.1%** (Failure) | $\ge \mathbf{72.0\%}$ |
| **Short Recall** | 85.0% | 95.2% | $\ge \mathbf{88.0\%}$ |
| **Short mAP@50-95** | 36.8% | 32.4% | $\ge \mathbf{38.0\%}$ |
