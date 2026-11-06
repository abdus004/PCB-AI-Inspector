"""
Google Colab Training Script for Experiment 1: Fine-Tuning models/best.pt on T4 GPU.

This script runs in Google Colab with Tesla T4 GPU (device=0).
Fine-tunes the existing checkpoint 'best.pt' without overwriting it.
Results are saved to a separate experiment directory.

Usage in Google Colab Cell:
    !python train_colab_exp1.py --weights /content/best.pt --data /content/pcb-yolo-final/data.yaml --epochs 40 --batch 16
"""

import argparse
import os
from pathlib import Path
import torch
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(description="Colab Experiment 1 Fine-Tuning")
    parser.add_argument("--weights", type=str, default="/content/best.pt",
                        help="Path to existing trained weights (best.pt)")
    parser.add_argument("--data", type=str, default="/content/pcb-yolo-final/data.yaml",
                        help="Path to data.yaml dataset config")
    parser.add_argument("--epochs", type=int, default=40, help="Number of fine-tuning epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (T4 supports 16 for imgsz=640)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--lr0", type=float, default=0.0005, help="Initial learning rate for fine-tuning")
    parser.add_argument("--project", type=str, default="/content/runs/experiments",
                        help="Project directory for outputs")
    parser.add_argument("--name", type=str, default="exp1_finetune_best",
                        help="Experiment run name")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("PCB-AI-Inspector: Experiment 1 Fine-Tuning on Colab T4")
    print("=" * 70)

    # Verify CUDA / GPU availability
    if not torch.cuda.is_available():
        print("WARNING: CUDA is not available! Please enable T4 GPU in Colab:")
        print("  Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU")
        device = "cpu"
    else:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"GPU Detected: {gpu_name} ({gpu_mem:.1f} GB VRAM)")
        device = 0

    weights_path = Path(args.weights)
    if not weights_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {weights_path}. Please upload best.pt to Colab.")

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset config not found at: {data_path}. Please extract pcb-yolo-final.zip.")

    print(f"\nBase Checkpoint: {weights_path}")
    print(f"Dataset Config:  {data_path}")
    print(f"Output Target:   {args.project}/{args.name}")
    print(f"Target Epochs:   {args.epochs}")
    print(f"Batch Size:      {args.batch}")
    print(f"Learning Rate:   {args.lr0} (fine-tuning rate)")

    # Load existing PCB weights
    model = YOLO(str(weights_path))

    # Execute fine-tuning with justified, conservative hyperparameter set
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
        mosaic=0.5,        # Reduced from 1.0 to preserve small trace visibility
        mixup=0.0,         # Kept OFF: prevents synthetic ghost traces
        copy_paste=0.0,    # Kept OFF: rectangular pasting harms dense PCB traces
        degrees=0.0,       # Kept OFF: dataset already contains 90/270 rotations
        fliplr=0.5,        # Horizontal flip
        flipud=0.0,        # Kept OFF: maintains standard component orientation
        hsv_h=0.015,
        hsv_s=0.3,         # Reduced from 0.7 to avoid hue distortion on soldermask
        hsv_v=0.2,         # Reduced from 0.4: dataset already has l_light simulation
        patience=15,       # Early stopping patience
        save=True,
        project=args.project,
        name=args.name,
        exist_ok=False,    # Never overwrite previous runs
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("Fine-tuning completed successfully!")
    out_dir = Path(args.project) / args.name
    print(f"Results and weights saved to: {out_dir}")
    print(f"Best fine-tuned weights:      {out_dir / 'weights' / 'best.pt'}")
    print("=" * 70)

    # Run validation on the new best checkpoint at standard settings (conf=0.25, iou=0.60)
    best_weights = out_dir / "weights" / "best.pt"
    if best_weights.exists():
        print("\nRunning post-training validation on validation split...")
        val_model = YOLO(str(best_weights))
        val_metrics = val_model.val(
            data=str(data_path),
            split="val",
            imgsz=args.imgsz,
            conf=0.25,
            iou=0.60,
            project=args.project,
            name=f"{args.name}_val",
        )
        print("\nValidation Results Summary:")
        print(f"  Precision: {val_metrics.results_dict.get('metrics/precision(B)', 0):.4f}")
        print(f"  Recall:    {val_metrics.results_dict.get('metrics/recall(B)', 0):.4f}")
        print(f"  mAP@50:    {val_metrics.results_dict.get('metrics/mAP50(B)', 0):.4f}")
        print(f"  mAP@50-95: {val_metrics.results_dict.get('metrics/mAP50-95(B)', 0):.4f}")


if __name__ == "__main__":
    main()
