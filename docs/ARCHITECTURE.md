# Architecture

## Overview

The pipeline processes traffic video through a chain of independent modules, each handling one step:

```
Input Video → VideoProcessor → VehicleDetector → MultiObjectTracker
                                                        ↓
                                        HomographyTransformer + SpeedEstimator
                                                        ↓
                                                TrafficAnalyzer
                                                        ↓
                              annotated_video.mp4 / vehicle_data.csv / traffic_summary.json
```

Detailed data flow:

```
                               +-----------------------------+
                               |     Input Video Stream      |
                               |  (MP4 / AVI / 4K UHD 50FPS) |
                               +--------------+--------------+
                                              |
                                              v
                               +-----------------------------+
                               |       VideoProcessor        |
                               | (Frame Ingestion & Control) |
                               +--------------+--------------+
                                              |
                                              v
                               +-----------------------------+
                               |       VehicleDetector       |
                               |   (YOLO11n / OpenCV MOG2)   |
                               +--------------+--------------+
                                              | Detections [bbox, centroid, class, conf]
                                              v
                               +-----------------------------+
                               |     MultiObjectTracker      |
                               | (Centroid Distance + IoU)   |
                               +--------------+--------------+
                                              | Persistent Tracks [track_id, history, bbox]
                                              v
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
        +-----------------------------+               +-----------------------------+
        |    HomographyTransformer    |               |       SpeedEstimator        |
        |  (Planar 4-Point Homography)| ------------> | (Smoothed Temporal Velocity)|
        +-----------------------------+ (World Coord) +--------------+--------------+
                                                                     |
                                                                     v
                                                      +-----------------------------+
                                                      |       TrafficAnalyzer       |
                                                      | (Statistical Aggregation)   |
                                                      +--------------+--------------+
                                                                     |
                                      +------------------------------+------------------------------+
                                      |                              |                              |
                                      v                              v                              v
                        +---------------------------+  +---------------------------+  +---------------------------+
                        |    Annotated MP4 Video    |  |     vehicle_data.csv      |  |   traffic_summary.json    |
                        +---------------------------+  +---------------------------+  +---------------------------+
```

---

## Module Details

### VideoProcessor (`src/video_processor.py`)
Orchestrates the pipeline. Reads frames with `cv2.VideoCapture`, optionally skips frames for performance (`--skip N`), pipes each frame through detection → tracking → speed → visualization, and writes the annotated output to MP4 + CSV.

### VehicleDetector (`src/detector.py`)
Two detection backends:

1. **YOLO** (default) — Ultralytics YOLO11n, filtered to COCO vehicle classes (car, motorcycle, bus, truck). Configurable confidence (`--conf`) and input resolution (`--imgsz`).
2. **MOG2** — OpenCV Gaussian mixture background subtractor with morphological opening/closing for noise cleanup. Included to compare motion-based detection against semantic detection.

### MultiObjectTracker (`src/tracker.py`)
Maintains vehicle identities across frames. Associates detections using a combination of Euclidean centroid distance (bounded by `--max-distance`) and bounding-box IoU with class consistency. Tracks survive through occlusions for up to `--max-missed` frames before being retired.

### HomographyTransformer (`src/homography.py`)
Computes a 3×3 projective homography matrix **H** from 4 coplanar ground landmarks:

$$\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} \sim \mathbf{H} \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}$$

This maps pixel coordinates on the road surface to real-world metre coordinates. The 4 point pairs are stored in `config/calibration.json`.

### SpeedEstimator (`src/speed_estimator.py`)
Keeps a sliding window of the last 5 centroid positions for each track. Speed is computed as:

```
displacement = sqrt((X_t - X_{t-n})^2 + (Y_t - Y_{t-n})^2)
time = n / FPS
speed = displacement / time
```

If homography is active, displacement is in metres → speed in m/s. Otherwise it's pixels → pixels/s. An upper-bound filter (38 m/s ≈ 137 km/h) suppresses spurious spikes from horizon-projection singularities.

### TrafficAnalyzer (`src/traffic_analyzer.py`)
Aggregates per-frame data into summary statistics:
- **Vehicle counts** by class, fleet modal split, heavy vehicle percentage
- **Speed stats**: mean, max, standard deviation, coefficient of variation, 85th and 15th percentile speeds
- **Density**: vehicles per lane-km
- **Congestion level**: Light / Moderate / Heavy
- **HCM Level of Service**: A through F, based on density and speed thresholds from the Highway Capacity Manual

### Visualizer (`src/visualizer.py`)
Draws bounding boxes, vehicle IDs, speed labels, trajectory trails, and a semi-transparent HUD banner onto each frame. Typography and box sizes scale with video resolution (works from 720p to 4K).

---

## Data Schemas

### Calibration (`config/calibration.json`)
```json
{
  "camera": "Fixed traffic surveillance camera",
  "resolution": "3840x2160",
  "image_points": [[1450, 1450], [2900, 1450], [3500, 2160], [600, 2160]],
  "world_points": [[0.0, 40.0], [14.0, 40.0], [14.0, 0.0], [0.0, 0.0]],
  "units": { "world_coordinates": "metres", "speed": "m/s and km/h" }
}
```

### Vehicle CSV (`outputs/vehicle_data.csv`)
| Column | Type | Description |
|---|---|---|
| frame | int | Frame index (0-based) |
| vehicle_id | int | Persistent track ID |
| class | str | Vehicle type (car, bus, truck) |
| confidence | float | Detection confidence [0, 1] |
| x, y | int | Centroid pixel coordinates |
| width, height | int | Bounding box size |
| speed | float | Velocity (m/s or px/s) |
| speed_unit | str | "m/s" or "pixels/s" |
| speed_kmh | float/str | Speed in km/h, or "N/A" if uncalibrated |

### Summary JSON (`outputs/traffic_summary.json`)
Contains: frames processed, unique tracks, average/peak active vehicles, density, HCM LOS rating, congestion level, hourly flow rate, detection counts by class, modal split, speed stats (mean, max, std dev, V85, V15), calibration status, and resolution/FPS metadata.

---

## Error Handling

1. **Missing video**: exits with a clear error message and return code 1 (no Python traceback).
2. **Missing calibration**: tries `config/calibration.json`, then `config/calibration.example.json`, then synthesizes a default geometry from the video's resolution. Never crashes.
3. **Headless execution**: `QT_QPA_PLATFORM=offscreen` is set at import time. No `cv2.imshow()` calls in the pipeline, so it runs on servers, Docker, and CI without a display.
