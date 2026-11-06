"""
Google Colab Training Script for Experiment 2: Controlled Fine-Tuning.

Experiment 2 Configuration:
- Base Checkpoint: Original 30-epoch training run's best.pt (verified: pcb_finetune_30epochs)
- Default Weights Path: /content/drive/MyDrive/PCB_AI_Inspector/trained_models/pcb_finetune_30epochs/best.pt
- Epochs: 20
- Batch Size: 16
- Image Size: 640
- Optimizer: AdamW
- Initial Learning Rate (lr0): 0.0003
- Early-Stopping Patience: 8
- Loss Gains: box=7.5, cls=0.5, dfl=1.5
- Augmentations: mosaic=0.5, mixup=0.0, copy_paste=0.0, degrees=0.0,
                 fliplr=0.5, flipud=0.0, hsv_h=0.015, hsv_s=0.3, hsv_v=0.2
- Destination: /content/runs/experiments/exp2_controlled_finetune
- Safety: exist_ok=False (never overwrites existing checkpoints or runs)
- Checkpoint Protection: Hard exception raised if Experiment 1 weights are supplied.

Post-Training Evaluations (Separate Directories):
- A. Standard Validation: default benchmark settings (mAP PR-curve evaluation) -> exp2_controlled_finetune_val_standard
- B. Operational Validation: conf=0.25, iou=0.60 (deployment inspection metrics) -> exp2_controlled_finetune_val_operational

Usage in Google Colab Cell:
    !python train_colab_exp2.py \
        --weights /content/drive/MyDrive/PCB_AI_Inspector/trained_models/pcb_finetune_30epochs/best.pt \
        --data /content/pcb_colab.yaml \
        --epochs 20 \
        --batch 16 \
        --lr0 0.0003 \
        --patience 8 \
        --project /content/runs/experiments \
        --name exp2_controlled_finetune
"""

import argparse
import sys
from pathlib import Path
import torch
from ultralytics import YOLO


DEFAULT_WEIGHTS_PATH = (
    "/content/drive/MyDrive/PCB_AI_Inspector/trained_models/"
    "pcb_finetune_30epochs/best.pt"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="PCB-AI-Inspector: Experiment 2 Controlled Fine-Tuning on Colab T4"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=DEFAULT_WEIGHTS_PATH,
        help=(
            "Path to original 30-epoch training run best.pt checkpoint "
            f"(default: {DEFAULT_WEIGHTS_PATH})"
        ),
    )
    parser.add_argument(
        "--data",
        type=str,
        default="/content/pcb_colab.yaml",
        help="Path to dataset YAML configuration file",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=20,
        help="Maximum fine-tuning epochs (default: 20)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size for training (default: 16)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Input image resolution (default: 640)",
    )
    parser.add_argument(
        "--lr0",
        type=float,
        default=0.0003,
        help="Initial learning rate for fine-tuning (default: 0.0003)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=8,
        help="Early stopping patience in epochs (default: 8)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default="/content/runs/experiments",
        help="Base directory for experiment outputs",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="exp2_controlled_finetune",
        help="Subdirectory name for this experiment run",
    )
    return parser.parse_args()


def verify_checkpoint(weights_path: Path):
    """
    Inspect checkpoint metadata.
    Raises an exception and halts execution if:
    1. The checkpoint does not exist.
    2. The checkpoint is identified as Experiment 1.
    3. The checkpoint does not match the original 30-epoch training run.
    """
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found at: {weights_path.resolve()}\n"
            "Please ensure the original checkpoint from the 30-epoch run is present."
        )

    ckpt = torch.load(weights_path, map_location="cpu", weights_only=False)
    train_args = ckpt.get("train_args", {})
    train_results = ckpt.get("train_results", {})
    run_name = str(train_args.get("name", ""))

    # 1. Reject Experiment 1 checkpoints unconditionally
    if "exp1" in run_name.lower() or "exp1" in str(weights_path).lower():
        raise ValueError(
            f"REFUSING TO TRAIN: Checkpoint at {weights_path} is identified as Experiment 1 "
            f"(internal run name: '{run_name}').\n"
            "Experiment 2 must strictly initialize from the ORIGINAL 30-epoch training checkpoint "
            "(pcb_finetune_30epochs). Contaminating Exp 2 with Exp 1 weights would entrench Short false positives."
        )

    # 2. Verify that this is the intended original 30-epoch checkpoint
    is_original = (
        run_name == "pcb_finetune_30epochs"
        or train_args.get("epochs") == 30
    )
    if not is_original:
        raise ValueError(
            f"CHECKPOINT VERIFICATION FAILED: The file at {weights_path} does not match "
            "the intended original 30-epoch training checkpoint.\n"
            f"Expected run name: 'pcb_finetune_30epochs' with 30 scheduled epochs.\n"
            f"Actual found: run name='{run_name}', epochs={train_args.get('epochs')}."
        )

    print("\n--- Base Checkpoint Verified Successfully ---")
    print(f"File Path:            {weights_path.resolve()}")
    print(f"Source Run Name:      {run_name}")
    print(f"Scheduled Epochs:     {train_args.get('epochs')}")
    print(f"Training Date:        {ckpt.get('date', 'Unknown')}")
    print(f"Ultralytics Version:  {ckpt.get('version', 'Unknown')}")
    if "epoch" in train_results:
        epochs_logged = len(train_results.get("epoch", []))
        print(f"Recorded History:     {epochs_logged} epochs logged (stopped at early-stopping point)")
    metrics = ckpt.get("train_metrics", {})
    if metrics:
        print(f"Source Peak mAP50:    {metrics.get('metrics/mAP50(B)', 0):.4f}")
        print(f"Source Peak mAP50-95: {metrics.get('metrics/mAP50-95(B)', 0):.4f}")
    print("---------------------------------------------\n")


def main():
    args = parse_args()

    print("=" * 75)
    print("PCB-AI-Inspector: Experiment 2 (Controlled Fine-Tuning on Colab T4)")
    print("=" * 75)

    # 1. Device check (strictly require CUDA GPU; do not fall back to CPU)
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available! Training on CPU is disabled for safety.\n"
            "Please enable a GPU accelerator in Google Colab:\n"
            "  Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU"
        )

    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    print(f"[GPU DETECTED] {gpu_name} ({gpu_mem:.2f} GB VRAM)")
    device = 0

    # 2. Strict Checkpoint Verification (halts execution if invalid or Exp 1)
    weights_path = Path(args.weights)
    verify_checkpoint(weights_path)

    # 3. Dataset YAML verification
    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset config not found at: {data_path.resolve()}\n"
            "Please ensure pcb_colab.yaml or data.yaml exists."
        )

    # 4. Safety: prevent overwriting existing experiment runs
    dest_dir = Path(args.project) / args.name
    if dest_dir.exists():
        raise FileExistsError(
            f"Target directory already exists: {dest_dir.resolve()}\n"
            "Safety rule enforced: exist_ok=False. "
            "Please rename --name or archive the existing folder to preserve all experiments."
        )

    print("Experiment 2 Training Hyperparameters:")
    print(f"  Base Model:          {weights_path}")
    print(f"  Dataset Config:      {data_path}")
    print(f"  Max Epochs:          {args.epochs}")
    print(f"  Batch Size:          {args.batch}")
    print(f"  Image Size:          {args.imgsz}")
    print(f"  Optimizer:           AdamW")
    print(f"  Initial LR (lr0):    {args.lr0}")
    print(f"  LR Final Ratio(lrf): 0.01")
    print(f"  Warmup Epochs:       2")
    print(f"  Patience:            {args.patience}")
    print(f"  Loss Gains:          box=7.5, cls=0.5, dfl=1.5")
    print(f"  Augmentations:       mosaic=0.5, mixup=0.0, copy_paste=0.0, degrees=0.0,")
    print(f"                       fliplr=0.5, flipud=0.0, hsv_h=0.015, hsv_s=0.3, hsv_v=0.2")
    print(f"  Destination:         {dest_dir}")
    print("=" * 75)

    # 5. Initialize model from verified original checkpoint
    model = YOLO(str(weights_path))

    # 6. Execute training with verified hyperparameter set
    print("\nStarting Experiment 2 controlled fine-tuning...\n")
    train_results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=device,
        optimizer="AdamW",
        lr0=args.lr0,
        lrf=0.01,
        warmup_epochs=2,
        weight_decay=0.0005,
        patience=args.patience,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        mosaic=0.5,
        mixup=0.0,
        copy_paste=0.0,
        degrees=0.0,
        fliplr=0.5,
        flipud=0.0,
        hsv_h=0.015,
        hsv_s=0.3,
        hsv_v=0.2,
        save=True,
        project=args.project,
        name=args.name,
        exist_ok=False,
        verbose=True,
    )

    print("\n" + "=" * 75)
    print("Experiment 2 Training Complete!")
    print(f"Run outputs saved to: {dest_dir}")
    best_pt = dest_dir / "weights" / "best.pt"
    print(f"New Best Weights:     {best_pt}")
    print("=" * 75)

    # 7. Post-training dual validation (Validation Split Only)
    if not best_pt.exists():
        raise FileNotFoundError(
            f"Expected trained weights file not found at: {best_pt.resolve()}\n"
            "Training may have terminated abnormally or failed to produce weights."
        )

    eval_model = YOLO(str(best_pt))

    # A. Standard Benchmark Validation
    # Default conf=0.001, iou=0.70 to build full PR-curves and exact mAP50 / mAP50-95
    std_name = f"{args.name}_val_standard"
    print("\n" + "=" * 75)
    print("A. Running Standard Benchmark Validation (Full PR-curve mAP settings)...")
    print(f"   Destination: {Path(args.project) / std_name}")
    print("=" * 75)
    std_metrics = eval_model.val(
        data=str(data_path),
        split="val",
        imgsz=args.imgsz,
        project=args.project,
        name=std_name,
        exist_ok=False,
        verbose=True,
    )
    print("\n=== Standard Validation Results (Benchmark Comparison) ===")
    print(f"  Precision: {std_metrics.results_dict.get('metrics/precision(B)', 0):.4f}")
    print(f"  Recall:    {std_metrics.results_dict.get('metrics/recall(B)', 0):.4f}")
    print(f"  mAP@50:    {std_metrics.results_dict.get('metrics/mAP50(B)', 0):.4f}")
    print(f"  mAP@50-95: {std_metrics.results_dict.get('metrics/mAP50-95(B)', 0):.4f}")

    # B. Operational Validation
    # Deployment threshold: conf=0.25, iou=0.60
    op_name = f"{args.name}_val_operational"
    print("\n" + "=" * 75)
    print("B. Running Operational Validation (conf=0.25, iou=0.60)...")
    print(f"   Destination: {Path(args.project) / op_name}")
    print("=" * 75)
    op_metrics = eval_model.val(
        data=str(data_path),
        split="val",
        imgsz=args.imgsz,
        conf=0.25,
        iou=0.60,
        project=args.project,
        name=op_name,
        exist_ok=False,
        verbose=True,
    )
    print("\n=== Operational Validation Results (conf=0.25, iou=0.60) ===")
    print(f"  Precision: {op_metrics.results_dict.get('metrics/precision(B)', 0):.4f}")
    print(f"  Recall:    {op_metrics.results_dict.get('metrics/recall(B)', 0):.4f}")
    print(f"  mAP@50:    {op_metrics.results_dict.get('metrics/mAP50(B)', 0):.4f}")
    print(f"  mAP@50-95: {op_metrics.results_dict.get('metrics/mAP50-95(B)', 0):.4f}")
    print("=" * 75)
    print(f"\nBoth validation evaluations completed and saved to separate directories:")
    print(f"  Standard Benchmark: {Path(args.project) / std_name}")
    print(f"  Operational Check:  {Path(args.project) / op_name}")


if __name__ == "__main__":
    main()
