# audit_filenames.py -- READ-ONLY. Reads filenames, image headers and label text only (no pixels).
# Writes reports/manifest_all.csv. Run from the project root with the venv active.
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image

BASE = Path("datasets/pcb-defect-dataset")
OUT = Path("reports")
OUT.mkdir(exist_ok=True)
SPLITS = ("train", "val", "test")
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
NAMES = yaml.safe_load(open("configs/data.yaml", encoding="utf-8"))["names"]
ID_OF = {v: int(k) for k, v in NAMES.items()}
PAT = re.compile(r"^(?P<prefix>.*?)light_(?P<board>\d+)_(?P<defect>.+)_(?P<src>\d+)_(?P<crop>\d+)_(?P<tag>\d+)$")

rows, unparsed = [], []
for s in SPLITS:
    for p in sorted((BASE / s / "images").iterdir()):
        if p.suffix.lower() not in EXT:
            continue
        m = PAT.match(p.stem)
        if not m:
            unparsed.append(f"{s}/{p.name}")
            continue
        d = m.groupdict()
        with Image.open(p) as im:                     # header only, pixels are not decoded
            w, h = im.size
        lp = BASE / s / "labels" / (p.stem + ".txt")
        lab = [l.split() for l in lp.read_text(encoding="utf-8").splitlines() if l.strip()] if lp.exists() else []
        rows.append(dict(split=s, file=p.name, variant=d["prefix"] + "light", board=d["board"],
                         defect=d["defect"], src=d["src"], crop=d["crop"], tag=d["tag"],
                         width=w, height=h, n_boxes=len(lab),
                         classes=" ".join(sorted(l[0] for l in lab))))
with open(OUT / "manifest_all.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0]))
    wr.writeheader()
    wr.writerows(rows)

print(f"parsed {len(rows)} filenames; unparsed: {len(unparsed)} {unparsed[:5]}")


def table(title, keyfn):
    print(f"\n--- {title} ---")
    cnt = defaultdict(Counter)
    for r in rows:
        cnt[keyfn(r)][r["split"]] += 1
    for k in sorted(cnt):
        c = cnt[k]
        print(f"  {str(k):28s} train={c['train']:5d} val={c['val']:4d} test={c['test']:4d}  total={sum(c.values())}")


table("variant (filename prefix) x split", lambda r: r["variant"])
table("image size (w,h) by variant", lambda r: (r["variant"], r["width"], r["height"]))
table("board id x split", lambda r: r["board"])
table("filename defect type x split", lambda r: r["defect"])
print("distinct filename 'tag' values (last token):", sorted({r["tag"] for r in rows}))

# --- filename defect type vs label classes (a cheap check that labels belong to their images) ---
bad = [r for r in rows if r["classes"] == "" or set(r["classes"].split()) != {str(ID_OF.get(r["defect"], "?"))}]
print(f"\n--- filename defect vs label classes ---\n  files whose label classes != the defect named in the filename: "
      f"{len(bad)} of {len(rows)}  (empty label files: {sum(r['n_boxes'] == 0 for r in rows)})")
for r in bad[:8]:
    print("   ", r["split"], r["file"], "| classes in label file:", r["classes"] or "(none)")


# --- how do the variants relate? group by the 'crop id' = board + defect + source image + crop index ---
def spans(keyfn, label):
    g = defaultdict(list)
    for r in rows:
        g[keyfn(r)].append(r)
    multi = [v for v in g.values() if len({x["split"] for x in v}) > 1]
    imgs_in_multi = sum(len(v) for v in multi)
    print(f"  {label}: {len(g)} groups; {len(multi)} span more than one split "
          f"({imgs_in_multi} of {len(rows)} images = {imgs_in_multi / len(rows):.0%})")
    return g


print("\n--- candidate grouping keys (do groups straddle splits?) ---")
crop_id = spans(lambda r: (r["board"], r["defect"], r["src"], r["crop"]), "crop id (board, defect, src, crop)")
spans(lambda r: (r["board"], r["defect"], r["src"]), "source image (board, defect, src)")
spans(lambda r: (r["board"], r["defect"]), "board + defect type")
spans(lambda r: r["board"], "board only")
print("\n  variants per crop id:", dict(Counter(len({x["variant"] for x in v}) for v in crop_id.values())))
mism = [k for k, v in crop_id.items() if len(v) > 1 and len({(x["n_boxes"], x["classes"]) for x in v}) > 1]
print(f"  crop ids whose variants disagree on box count or classes: {len(mism)} of {len(crop_id)}  e.g. {mism[:3]}")
print(f"\nManifest written to {(OUT / 'manifest_all.csv').resolve()}")