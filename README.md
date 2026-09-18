# Traffic Vision Analytics

A computer vision pipeline that takes traffic surveillance video, detects and tracks vehicles across frames, corrects for camera perspective using homography, estimates real-world vehicle speeds, and exports the results as annotated video, CSV logs, and a JSON summary.

Built with OpenCV and Ultralytics YOLO11n. Runs entirely from the command line — no GUI or display server needed.

![Annotated traffic frame showing detection, tracking, and speed overlays](docs/demo_preview.jpg)

---

## Quick Start

A small sample video (`data/sample_traffic.mp4`) is included in the repo so you can run the pipeline immediately after cloning.

### 1. Setup

```bash
git clone https://github.com/Devansh-Bansal-AI/traffic-vision-analytics.git
cd traffic-vision-analytics

# Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run Tests

```bash
python -m pytest -v
```

Expected: `13 passed`.

### 3. Run the Pipeline

```bash
python main.py --input data/sample_traffic.mp4 --max-frames 50
```

The system auto-loads `config/calibration.json` for perspective correction. If the file is missing, it generates a default geometry from the video dimensions — no manual config needed.

All output goes to `outputs/` (annotated video, CSV, JSON). No desktop windows are opened; progress prints to stdout.

> To use your own video, just place it in `data/` and pass the path via `--input`.

---

## How Speed Measurement Works

### Calibrated Mode (default)

The pipeline uses a 3×3 homography matrix computed from 4 ground-plane landmarks (`config/calibration.json`) to convert pixel motion into real-world distances in metres. Speed is then:

```
v = displacement_metres / time_seconds
```

Reported in both m/s and km/h on the bounding box overlays, CSV, and JSON.

### Uncalibrated Mode

Without calibration (pass `--uncalibrated`), speed is reported in pixels/s. Useful if you don't have reference points for your video.

```bash
python main.py --input data/sample_traffic.mp4 --uncalibrated --max-frames 50
```

### MOG2 Baseline Detector

To compare YOLO detection against classical background subtraction:

```bash
python main.py --input data/sample_traffic.mp4 --detector mog2 --max-frames 50
```

Uses `cv2.createBackgroundSubtractorMOG2` with morphological filtering. Highlights the difference between motion-based segmentation and semantic detection (e.g., MOG2 loses stationary vehicles at red lights).

---

## Outputs

Every run produces three files in `outputs/`:

### `annotated_video.mp4`
Video with bounding boxes, vehicle IDs, trajectory trails, speed labels (km/h or px/s), and a HUD banner showing frame count, active vehicles, and class breakdown.

### `vehicle_data.csv`
One row per tracked vehicle per frame:
```csv
frame,vehicle_id,class,confidence,x,y,width,height,speed,speed_unit,speed_kmh
0,1,car,0.8969,1997,1608,488,374,0.0000,m/s,0.00
1,1,car,0.9007,1997,1607,490,376,1.0000,m/s,3.60
```

### `traffic_summary.json`
Aggregated stats for the whole run:
```json
{
  "frames_processed": 20,
  "unique_vehicle_tracks": 8,
  "average_active_vehicles_per_frame": 6.45,
  "congestion_level": "Moderate",
  "total_vehicle_detections": 129,
  "vehicle_detections_by_class": {"car": 107, "bus": 19, "truck": 3},
  "average_speed_kmh": 15.92,
  "maximum_speed_kmh": 78.51,
  "speed_calibrated": true
}
```

---

## CLI Options

```text
usage: main.py [-h] --input INPUT [--output-dir OUTPUT_DIR]
               [--detector {yolo,mog2}] [--model MODEL] [--conf CONF]
               [--imgsz IMGSZ] [--device DEVICE]
               [--max-distance MAX_DISTANCE] [--max-missed MAX_MISSED]
               [--iou-threshold IOU_THRESHOLD] [--min-area MIN_AREA]
               [--calibration CALIBRATION] [--max-frames MAX_FRAMES]
               [--skip SKIP] [--show]
```

Some useful flags:
- `--skip N` — process every (N+1)th frame. Useful for speeding up 4K video on CPU.
- `--imgsz 640` — inference resolution (default 640px).
- `--device cuda` — use GPU if available.
- `--show` — open a live preview window (only works on a desktop with a display).
- `--conf 0.35` — detection confidence threshold.
- `--calibration path/to/file.json` — use a custom calibration file.
- `--uncalibrated` — force pixel-based speed (no homography).

---

## Test Suite

```bash
python -m pytest -v
```

13 tests covering:
- Bounding-box IoU computation
- Tracker persistence across frames
- Homography coordinate transforms
- Speed calculation (calibrated m/s → km/h conversion)
- Traffic analyzer congestion classification
- HCM Level of Service evaluation
- Operating speed percentiles (V85, V15)
- MOG2 detector initialization
- Configuration fallback when calibration files are missing

---

## Project Structure

```text
traffic-vision-analytics/
├── main.py                      # CLI entry point
├── requirements.txt             # Dependencies
├── README.md
├── statement.md                 # Project problem statement
├── LICENSE                      # MIT
├── config/
│   ├── calibration.json         # 4-point homography calibration
│   └── calibration.example.json # Template for custom calibrations
├── src/
│   ├── __init__.py
│   ├── detector.py              # YOLO and MOG2 detection
│   ├── tracker.py               # Multi-object tracking (centroid + IoU)
│   ├── homography.py            # Perspective transform
│   ├── speed_estimator.py       # Velocity estimation
│   ├── traffic_analyzer.py      # Stats aggregation and congestion classification
│   ├── visualizer.py            # Bounding boxes, HUD, trajectory rendering
│   └── video_processor.py       # Frame loop, CSV/MP4 output
├── tests/
│   ├── test_analyzer.py
│   ├── test_homography.py
│   ├── test_pipeline_integration.py
│   ├── test_speed.py
│   └── test_tracker.py
├── scripts/
│   └── generate_pdf_report.py   # Builds the PDF report from markdown
├── data/
│   ├── sample_traffic.mp4       # Small sample clip (committed for quick evaluation)
│   └── README.md
├── outputs/
│   ├── vehicle_data.csv         # Example output from a sample run
│   ├── traffic_summary.json     # Example output from a sample run
│   └── sample_annotated_frame_150.jpg
├── docs/
│   ├── ARCHITECTURE.md          # System design and math
│   └── demo_preview.jpg
└── report/
    ├── PROJECT_REPORT.md        # Full project report
    └── PROJECT_REPORT.pdf       # PDF version for portal upload
```

---

## Documentation

- [Project Report (PDF)](report/PROJECT_REPORT.pdf) — for portal submission
- [Project Report (Markdown)](report/PROJECT_REPORT.md)
- [Architecture & Technical Details](docs/ARCHITECTURE.md)
- [Problem Statement](statement.md)
- [Calibration Config](config/calibration.json)

---

## License

MIT — see [LICENSE](LICENSE).
