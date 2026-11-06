# PCB-AI-Inspector

AI-assisted PCB defect inspection. Upload or capture a photo of a printed circuit board, run your
trained **YOLO11n** model through a FastAPI backend, review annotated results, keep a local
inspection history (SQLite) and download a PDF report.

Three screens only: **Landing**, **Inspection**, **Results**.

> **Important limitation.** The model was evaluated on a held-out test set containing only **two PCB boards**
> (Precision 87.8%, Recall 89.3%, mAP@50 92.1%, mAP@50–95 41.5%). These are experimental results, not a guarantee of
> real-world performance. The model recognises six defect types only, and "No Visible Defect Detected" never means a board is defect-free.

## Project layout

```
PCB-AI-Inspector/
├── models/best.pt              <- YOUR trained weights (not in this ZIP; leave untouched)
├── configs/                    <- your existing YAML files (unchanged)
├── backend/
│   ├── main.py                 FastAPI app and all routes
│   ├── config.py               paths, limits, thresholds, CORS
│   ├── database.py             SQLite helpers
│   ├── requirements.txt
│   ├── .env.example
│   ├── services/
│   │   ├── images.py           image validation, thumbnails
│   │   ├── model.py            loads best.pt once, runs YOLO (thread-safe)
│   │   ├── inspection.py       unified workflow, history, delete
│   │   └── report.py           PDF report (ReportLab)
│   ├── storage/                originals/ annotated/ reports/ thumbnails/  (created automatically)
│   └── inspections.db          created automatically on first start
└── frontend/                   React 19 + Vite + Tailwind CSS 4
    └── src/
        ├── App.jsx             picks the page from the URL
        ├── pages/              LandingPage, InspectionPage, ResultsPage
        ├── components/         Header, Link, UploadZone, CameraCapture, HistoryList,
        │                       ImageViewer, DetectionList, PcbHero, ui, Logo
        ├── services/api.js    the ONLY place that talks to the backend
        ├── lib/                router, validation, formatting, status styles
        └── data/content.js     landing-page text and the model metrics
```

## Requirements

* Python 3.10 or newer, Node.js 20 or newer
* Your trained weights at `models/best.pt` (this project never replaces or retrains them)

## Run it (Windows PowerShell)

Backend (terminal 1), from the project root:

```powershell
cd backend
python -m venv ..\.venv          # skip if you already have a virtual environment
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (terminal 2):

```powershell
cd frontend
npm install
Copy-Item .env.example .env      # optional: only needed if the backend is not on 127.0.0.1:8000
npm run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs

The backend loads `models/best.pt` at startup and stops with a clear message if the file is missing.
Run `uvicorn` from inside the `backend` folder (as above) because the modules import each other by name.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/`, `/health`, `/model-info` | existing, unchanged |
| POST | `/predict` | existing: JSON detections (no saving) |
| POST | `/predict/annotated` | existing: annotated JPEG (no saving) |
| POST | `/inspect` | validate -> YOLO once -> annotate -> save -> full JSON (field name `file`) |
| GET | `/inspections?limit=&offset=` | history list |
| GET | `/inspections/{id}` | saved results (does **not** re-run YOLO) |
| GET | `/inspections/{id}/original` · `/annotated` · `/thumbnail` | images |
| GET | `/inspections/{id}/report` | PDF report (built on first request, then cached) |
| DELETE | `/inspections/{id}` | remove the record and its files |

Inspection IDs look like `PCB-20261103-1A2B3C`.

## How conclusions are decided

* **Potential Defect Detected**: at least one detection with confidence >= 25% (same threshold as `/predict`).
* **Inconclusive**: no detection >= 25%, but weaker candidates (10-25%) exist, or the image's shorter side is under 320 px.
* **No Visible Defect Detected**: nothing found. This is not proof of a defect-free board.

Thresholds live in `backend/config.py`. YOLO runs once per inspection at a 10% floor; only detections at or above 25% are listed
and drawn.

## Troubleshooting

* **Backend stops with "Model weights not found"**: put `best.pt` in `<project root>/models/` (or set `PCB_MODEL_PATH`).
* **Browser says "Cannot reach the inspection server"**: the backend is not running, or `VITE_API_BASE_URL` points to the wrong address.
  Restart the frontend dev server after editing `frontend/.env`.
* **CORS error in the console**: add your frontend address to `CORS_ORIGINS` in `backend/.env` and restart uvicorn.
* **First inspection is slow**: the first YOLO run warms up the model; later runs are faster.
* **History and images**: stored in `backend/inspections.db` and `backend/storage/`. Deleting an inspection removes its record and files.

## Notes

* Browsers only allow the camera on `https://` pages or `localhost`. On a phone using your PC's LAN address
  (`http://192.168...`) the camera tab will explain this; use Upload instead, which lets a phone take a photo directly.
* Settings: `CORS_ORIGINS` and `PCB_MODEL_PATH` can be set in `backend/.env` (see `.env.example`).
* The metrics shown on the landing page and in reports are exactly the ones you supplied; nothing else was invented.
* Back up `backend/inspections.db` and `backend/storage/` if you want to keep your history.
