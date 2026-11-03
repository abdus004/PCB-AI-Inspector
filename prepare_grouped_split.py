
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

MANIFEST_PATH = Path("reports/manifest_all.csv")
OUTPUT_PATH = Path("reports/grouped_split_proposal.csv")

# Load manifest
df = pd.read_csv(MANIFEST_PATH)

# Keep all variants of the same crop in one group
group_columns = ["board", "defect", "src", "crop"]
df["group_id"] = df[group_columns].astype(str).agg("_".join, axis=1)

# First split: 80% train, 20% temporary
first_split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42
)

train_idx, temp_idx = next(
    first_split.split(df, groups=df["group_id"])
)

train_df = df.iloc[train_idx].copy()
temp_df = df.iloc[temp_idx].copy()

# Second split: 50% validation, 50% test
second_split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.50,
    random_state=42
)

val_idx, test_idx = next(
    second_split.split(temp_df, groups=temp_df["group_id"])
)

# Assign split names
train_df["new_split"] = "train"
temp_df["new_split"] = ""

temp_df.loc[temp_df.index[val_idx], "new_split"] = "val"
temp_df.loc[temp_df.index[test_idx], "new_split"] = "test"

# Combine results
proposal = pd.concat(
    [train_df, temp_df],
    ignore_index=True
)

# Check group leakage
group_split_counts = proposal.groupby("group_id")["new_split"].nunique()
leaked_groups = group_split_counts[group_split_counts > 1]

# Save proposal only
proposal.to_csv(OUTPUT_PATH, index=False)

print("========== GROUPED SPLIT PROPOSAL ==========")
print("Total images:", len(proposal))

print("\nImage counts:")
print(proposal["new_split"].value_counts())

print("\nGroup counts:")
print(proposal.groupby("new_split")["group_id"].nunique())

print("\nGroups crossing splits:", len(leaked_groups))
print("Saved to:", OUTPUT_PATH)

if len(leaked_groups) == 0:
    print("\nSUCCESS: No crop groups cross splits.")
else:
    print("\nWARNING: Group leakage detected.")
