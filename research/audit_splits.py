# audit_splits.py  -- READ-ONLY. Run from the project root with the venv active.
from collections import Counter, defaultdict
from pathlib import Path
import cv2
import numpy as np

BASE = Path("datasets/pcb-defect-dataset")
SPLITS = ("train", "val", "test")
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def variant_hashes(thumb):
    """240-bit gradient hash for each of the 8 rotations/flips of a 16x16 thumbnail."""
    vs = [np.rot90(f, k) for f in (thumb, thumb[:, ::-1]) for k in range(4)]
    return np.stack([np.packbits((v[:, 1:] > v[:, :-1]).ravel()) for v in vs])  # [8, 30]


def nearest(query, ref):
    """Smallest Hamming distance from each query image (as-is) to any of ref's 8 variants."""
    q = query[:, 0, :]
    r = ref.reshape(-1, ref.shape[-1])
    best = np.empty(len(q), dtype=np.int32)
    who = np.empty(len(q), dtype=np.int64)
    for i in range(0, len(q), 64):
        d = POP[q[i:i + 64, None, :] ^ r[None, :, :]].sum(axis=2, dtype=np.int32)
        j = d.argmin(axis=1)
        best[i:i + 64] = d[np.arange(len(j)), j]
        who[i:i + 64] = j // 8
    return best, who


names, hashes, sizes, unreadable = {}, {}, {}, []
for s in SPLITS:
    paths = sorted(p for p in (BASE / s / "images").iterdir() if p.suffix.lower() in EXT)
    names[s], rows, sizes[s] = [], [], Counter()
    for p in paths:
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            unreadable.append(f"{s}/{p.name}")
            continue
        sizes[s][(g.shape[1], g.shape[0])] += 1          # (width, height)
        rows.append(variant_hashes(cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA)))
        names[s].append(p.name)
    hashes[s] = np.stack(rows)
    print(f"{s}: read {len(names[s])} images | sizes (w,h): {sizes[s].most_common(4)}")
    print(f"   sample names: {names[s][:3]}")
print("Unreadable images:", len(unreadable), unreadable[:5])

print("\n--- Do filename prefixes span splits? (drop last k '_' tokens) ---")
for k in (1, 2, 3):
    groups = defaultdict(set)
    for s in SPLITS:
        for n in names[s]:
            groups["_".join(Path(n).stem.split("_")[:-k])].add(s)
    multi = sum(len(v) > 1 for v in groups.values())
    print(f"k={k}: {len(groups)} groups, {multi} appear in more than one split")

print("\n--- Nearest-image distance across splits (0 = identical; ~120 = unrelated; max 240) ---")
for a, b in (("val", "train"), ("test", "train"), ("test", "val")):
    best, who = nearest(hashes[a], hashes[b])
    print(f"{a} -> {b}: n={len(best)}  median={int(np.median(best))}  "
          f"==0: {(best == 0).sum()}  <=12: {(best <= 12).sum()}  <=24: {(best <= 24).sum()}")
    for i in np.argsort(best)[:5]:
        print(f"    d={best[i]:3d}  {names[a][i]}  <->  {names[b][who[i]]}")