
import yaml
from ultralytics.data.utils import check_det_dataset

if __name__ == "__main__":
    data = check_det_dataset("configs/data.yaml")

    print("Resolved root:", data["path"])
    print("Train:", data["train"])
    print("Validation:", data["val"])
    print("Your class names:", data["names"])

    with open(
        "datasets/pcb-defect-dataset/data.yaml",
        encoding="utf-8"
    ) as file:
        kaggle_data = yaml.safe_load(file)

    print("Original Kaggle names:", kaggle_data["names"])
