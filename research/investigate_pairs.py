# investigate_pairs.py -- READ-ONLY on the dataset. Writes only to reports/pair_inspection/.
# Run from the project root with the venv active:  python investigate_pairs.py
import csv
import hashlib
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

BASE = Path("datasets/pcb-defect-dataset")
OUT = Path("reports/pair_inspection")
SPLITS = ("train", "val", "test")
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
NAMES = yaml.safe_load(open("configs/data.yaml", encoding="utf-8"))["names"]
N = 10                      # sampled pairs per category
rng = np.random.default_rng(0)
OUT.mkdir(parents=True, exist_ok=True)


def d8(a):
    """The 8 rotations/flips of a 2-D array."""
    return [np.ascontiguousarray(np.rot90(f, k)) for f in (a, a[:, ::-1]) for k in range(4)]


def group(name, k):
    """Filename stem with the last k '_' tokens dropped."""
    return "_".join(Path(name).stem.split("_")[:-k])


def labels_of(path, split):
    lp = BASE / split / "labels" / (path.stem + ".txt")
    if not lp.exists():
        return []
    rows = [l.split() for l in lp.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [(int(r[0]), *map(float, r[1:5])) for r in rows]


# ---------- 1. Load every image once: 64x64 thumbnail + the earlier 16x16 hash ----------
items = [(s, p) for s in SPLITS for p in sorted((BASE / s / "images").iterdir())
         if p.suffix.lower() in EXT]
split_of = np.array([s for s, _ in items])
thumbs = np.zeros((len(items), 64 * 64), np.float32)
hash16 = []
for i, (s, p) in enumerate(items):
    g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    thumbs[i] = cv2.resize(g, (64, 64), interpolation=cv2.INTER_AREA).ravel()
    t16 = cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA)
    hash16.append(np.packbits((t16[:, 1:] > t16[:, :-1]).ravel()).tobytes())
z = thumbs - thumbs.mean(axis=1, keepdims=True)
U = z / np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-6)   # dot product = Pearson r
idx = {s: np.flatnonzero(split_of == s) for s in SPLITS}
Q = np.concatenate([idx["val"], idx["test"]])
R = idx["train"]
name = lambda i: items[i][1].name

# ---------- 2. How informative was the 16x16 hash? ----------
cl = Counter(hash16)
print(f"\n[HASH] {len(items)} images -> {len(cl)} distinct 16x16 hashes; "
      f"largest identical-hash clusters: {[c for _, c in cl.most_common(5)]}")

# ---------- 3. Better retrieval: 64x64 correlation, best of 8 rotations/flips ----------
best = np.empty(len(Q), np.float32)
partner = np.empty(len(Q), np.int64)
UR = U[R]
for i in range(0, len(Q), 128):
    qi = Q[i:i + 128]
    V = np.concatenate([np.stack([v.ravel() for v in d8(U[j].reshape(64, 64))]) for j in qi])
    S = (V @ UR.T).reshape(len(qi), 8, -1).max(axis=1)
    partner[i:i + 128] = R[S.argmax(axis=1)]
    best[i:i + 128] = S.max(axis=1)
ctrl = (U[rng.choice(Q, 3000)] * U[rng.choice(R, 3000)]).sum(axis=1)
print("[CONTROL] correlation of RANDOM val/test-vs-train pairs (percentiles 5/50/95/99):",
      np.round(np.percentile(ctrl, [5, 50, 95, 99]), 3))
print("[RETRIEVAL] best train match per val/test image (64x64 correlation):")
for lo in (0.999, 0.99, 0.95, 0.90):
    print(f"   >= {lo}: {(best >= lo).sum()} of {len(best)}")
for k in (2, 3):
    same = np.array([group(name(q), k) == group(name(p), k) for q, p in zip(Q, partner)])
    hi = best >= 0.99
    print(f"   best partner shares the k={k} filename prefix: {same.mean():.0%} overall, "
          f"{(same[hi].mean() if hi.any() else float('nan')):.0%} among correlation>=0.99")

# ---------- 4. Choose pairs: top matches, filename-group pairs, random controls ----------
pairs = []
for lo, hi, label in ((0.99, 9, "best-match corr>=0.99"), (0.95, 0.99, "best-match corr 0.95-0.99"),
                      (-9, 0.95, "best-match corr<0.95")):
    sel = np.flatnonzero((best >= lo) & (best < hi))
    for j in rng.choice(sel, min(N, len(sel)), replace=False):
        pairs.append((label, int(Q[j]), int(partner[j])))
for k in (2, 3):
    by = {}
    for i in R:
        by.setdefault(group(name(i), k), []).append(int(i))
    pool = [int(q) for q in Q if group(name(q), k) in by]
    for q in rng.choice(pool, min(N, len(pool)), replace=False):
        pairs.append((f"same k={k} filename prefix", int(q), int(rng.choice(by[group(name(q), k)]))))
for q, p in zip(rng.choice(Q, N), rng.choice(R, N)):
    pairs.append(("random control", int(q), int(p)))


# ---------- 5. Full-resolution comparison ----------
def compare(A, B):
    h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    Af = A[:h, :w].astype(np.float32)
    best_r = None
    for t, Bt in enumerate(d8(B)):                       # best of 8 rotations/flips, offset 0
        Bf = Bt[:h, :w].astype(np.float32)
        r = float(np.nan_to_num(np.corrcoef(Af.ravel(), Bf.ravel())[0, 1]))
        if best_r is None or r > best_r[0]:
            best_r = (r, t, Bf)
    r, t, Bf = best_r
    gain = r * Af.std() / max(Bf.std(), 1e-6)
    diff = np.abs(Af - (gain * Bf + (Af.mean() - gain * Bf.mean())))   # allows brightness/contrast change
    m = cv2.morphologyEx((diff > 30).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    pts = cv2.findNonZero(m)
    bbox = cv2.boundingRect(pts) if pts is not None else None
    mae_raw = float(np.abs(Af - Bf).mean())
    max_raw = float(np.abs(Af - Bf).max())
    ts, shift = 0.0, None                                # shift-tolerant search (cropped/shifted copies)
    variants = d8(B)
    H, W = A.shape
    for y, x in ((H // 2 - 80, W // 2 - 80), (100, 100), (H - 260, W - 260)):
        patch = A[y:y + 160, x:x + 160]
        if patch.std() < 3:
            continue
        for tt, Bt in enumerate(variants):
            _, mx, _, loc = cv2.minMaxLoc(cv2.matchTemplate(Bt, patch, cv2.TM_CCOEFF_NORMED))
            if mx > ts:
                ts, shift = float(mx), (loc[0] - x, loc[1] - y, tt)
    frac = float(m.mean())
    if max_raw <= 2:
        verdict = "PIXEL-IDENTICAL (after transform)" if t else "PIXEL-IDENTICAL"
    elif r >= 0.98 and frac < 0.0005:
        verdict = "SAME IMAGE (brightness/JPEG-level change only)"
    elif r >= 0.90 and frac >= 0.0005:
        verdict = "SAME BASE IMAGE, LOCAL CHANGE"
    elif ts >= 0.90:
        verdict = "OVERLAPPING / SHIFTED CROP"
    else:
        verdict = "DIFFERENT"
    return dict(r=r, t=t, mae=mae_raw, frac=frac, bbox=bbox, ts=ts, shift=shift,
                verdict=verdict, diff=diff, hw=(h, w))


def panel(path, split):
    img = cv2.imread(str(path))
    H, W = img.shape[:2]
    sx, sy = 300 / W, 300 / H
    small = cv2.resize(img, (300, 300), interpolation=cv2.INTER_AREA)
    for c, xc, yc, bw, bh in labels_of(path, split):
        x1, y1 = int((xc - bw / 2) * W * sx) - 3, int((yc - bh / 2) * H * sy) - 3
        x2, y2 = int((xc + bw / 2) * W * sx) + 3, int((yc + bh / 2) * H * sy) + 3
        cv2.rectangle(small, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.putText(small, str(NAMES.get(c, c)), (x1, max(10, y1 - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
    return small


def corr64(q, p):
    return max(float(v.ravel() @ U[p]) for v in d8(U[q].reshape(64, 64)))


rows, records = [], []
for kind, q, p in pairs:
    (qs, qp), (ps, pp) = items[q], items[p]
    A = cv2.imread(str(qp), cv2.IMREAD_GRAYSCALE)
    B = cv2.imread(str(pp), cv2.IMREAD_GRAYSCALE)
    c = compare(A, B)
    same_file = hashlib.sha1(qp.read_bytes()).digest() == hashlib.sha1(pp.read_bytes()).digest()
    if same_file:
        c["verdict"] = "IDENTICAL FILE"
    cq = sorted({NAMES.get(l[0], l[0]) for l in labels_of(qp, qs)})
    cp = sorted({NAMES.get(l[0], l[0]) for l in labels_of(pp, ps)})
    h, w = c["hw"]
    heat = cv2.applyColorMap(np.clip(c["diff"] * 4, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
    heat = cv2.resize(heat, (300, 300))
    if c["bbox"]:
        x, y, bw, bh = c["bbox"]
        cv2.rectangle(heat, (int(x * 300 / w), int(y * 300 / h)),
                      (int((x + bw) * 300 / w), int((y + bh) * 300 / h)), (255, 255, 255), 1)
    row = np.full((300, 1500, 3), 30, np.uint8)
    row[:, 0:300], row[:, 300:600], row[:, 600:900] = panel(qp, qs), panel(pp, ps), heat
    lines = [f"[{kind}]", c["verdict"], f"Q {qs}/{qp.name}"[:62], f"P {ps}/{pp.name}"[:62],
             f"sizes {A.shape[::-1]} vs {B.shape[::-1]}  same file bytes: {same_file}",
             f"classes Q: {cq}  P: {cp}",
             f"corr64={corr64(q, p):.3f}  r_full={c['r']:.3f}  MAE={c['mae']:.1f}  transform#{c['t']}",
             f"changed_frac={c['frac']:.4f}  diff_bbox={c['bbox']}",
             f"template_score={c['ts']:.3f}  shift(dx,dy,transform)={c['shift']}"]
    for n, text in enumerate(lines):
        cv2.putText(row, text, (910, 30 + 30 * n), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255) if n < 2 else (200, 200, 200), 1)
    rows.append(row)
    records.append(dict(kind=kind, query=f"{qs}/{qp.name}", partner=f"{ps}/{pp.name}",
                        size_q=A.shape[::-1], size_p=B.shape[::-1], same_file=same_file,
                        classes_q=cq, classes_p=cp, r_full=round(c["r"], 4), mae=round(c["mae"], 2),
                        changed_frac=round(c["frac"], 5), diff_bbox=c["bbox"],
                        template=round(c["ts"], 3), shift=c["shift"], verdict=c["verdict"]))

for n in range(0, len(rows), 5):
    cv2.imwrite(str(OUT / f"sheet_{n // 5 + 1:02d}.png"), np.vstack(rows[n:n + 5]))
with open(OUT / "pairs.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(records[0]))
    wr.writeheader()
    wr.writerows(records)

# ---------- 6. Summary ----------
print("\n[PAIR VERDICTS] (heuristic labels; judge from the numbers and sheets, not the label alone)")
for kind in dict.fromkeys(r["kind"] for r in records):
    cnt = Counter(r["verdict"] for r in records if r["kind"] == kind)
    print(f"  {kind}: {dict(cnt)}")
print("\nFirst 12 sampled pairs:")
for r in records[:12]:
    print(f"  {r['verdict'][:28]:28s} r={r['r_full']:.3f} frac={r['changed_frac']:.4f} "
          f"tmpl={r['template']:.2f} | {r['query']} <-> {r['partner']} | {r['classes_q']} vs {r['classes_p']}")
print(f"\nSaved {len(rows)} pair rows in {(len(rows) + 4) // 5} sheets + pairs.csv -> {OUT.resolve()}")