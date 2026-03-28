<div align="center">

# 🏟️ CrowdView AI

**The Digital Twin for Venue Intelligence & Seat Occupancy**

[![YouTube Demo](https://img.shields.io/badge/YouTube-Watch_Demo-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtu.be/o1RCM11zGZo)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=ultralytics&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![Gemini](https://img.shields.io/badge/Gemini_2.0_Flash-8E75B2?style=for-the-badge&logo=googlebard&logoColor=white)](https://deepmind.google/technologies/gemini/)

<img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/LFkzRLsBIWXssxVJ.png" alt="CrowdView AI Dashboard" width="100%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

*CrowdView AI filters the noise of a 5,000-seat venue into actionable intelligence.*

</div>

---

## 🚀 Overview

**CrowdView AI** is a real-time computer vision and analytics platform designed to solve the "invisible loss" of premium empty seats at large-scale events. By combining **YOLOv8-Nano** object detection with a highly responsive **React** digital twin dashboard and **Google Gemini 2.0 Flash** intelligence, CrowdView AI empowers venue managers to instantly identify actionable vacancies and execute revenue-recovering maneuvers.

### 📺 Watch the Pitch & Demo
See CrowdView AI in action: **[Watch the 4-Minute Demo on YouTube](https://youtu.be/o1RCM11zGZo)**

> Developed for UTP Pitch Presentation • Prototype Level: **TRL 3** • **Version 1.0**

---

## ✨ Key Features

### 1. Live Vision Engine with Stability Logic
We don't just look for people; we look for *occupancy*. Our system uses a strict **60% spatial overlap rule** combined with a **30-second temporal confirmation**. This filters out the noise of crowds walking past chairs, ensuring zero false positives.

<div align="center">
  <img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/lqlXiyAQvFfHvgrX.png" alt="Temporal Confirmation Logic" width="48%">
  <img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/SuyBbbagTEQTKTaE.png" alt="Seat Status Close-up" width="48%">
  <p><em>Left: The system waits 30 seconds (yellow) to confirm occupancy. Right: Confirmed occupied (red) and actionable (orange) seats.</em></p>
</div>

### 2. The "Actionable" State
A green (empty) seat is just raw data. But if a premium seat remains empty past a critical grace period (e.g., 20 minutes into the main event), it becomes **Actionable (Orange)**. CrowdView highlights exactly where the problems are, reducing cognitive load for stage managers.

<div align="center">
  <img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/EtiGutwWKIyRjPFz.png" alt="Live Detection Dashboard" width="100%" style="border-radius: 8px;">
</div>

### 3. Gemini-Powered Intelligence Layer
When you click an actionable seat, our intelligence layer connects with the **Google Gemini 2.0 Flash API**. It instantly provides hyper-contextual operational maneuvers—like upgrading a prioritized standby guest to fill the front row immediately.

<div align="center">
  <img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/xMqiZuxHiWNdlOHq.png" alt="Live Event Analytics AI" width="80%" style="border-radius: 8px;">
</div>

### 4. Interactive Layout Editor
Every venue is unique. Our built-in Layout Editor allows you to drag, drop, and resize digital seats to perfectly match your physical space. You can even use Gemini to automatically generate layouts from a simple floor plan image.

<div align="center">
  <img src="https://files.manuscdn.com/user_upload_by_module/session_file/310519663442910604/IMZtamisyQIXwjlX.png" alt="Layout Editor Full" width="100%" style="border-radius: 8px;">
</div>

**Full feature list:**
- **Real-time Seat Detection** — YOLOv8-Nano (CPU-optimized) with area-based overlap logic
- **Temporal Confirmation** — 60% overlap sustained for 30s confirms occupancy; 20m grace period for vacancy
- **Time Tracking** — Flags seats as "actionable" when empty beyond zone-specific thresholds
- **AI Suggestions** — Gemini 2.0 Flash via OpenRouter for operational & energy insights
- **2D Digital Twin Dashboard** — React-based visualization with live seat status
- **Interactive Seat Calibration** — Click-to-place seat mapping with visual feedback
- **Auto-Calibration** — Gemini + OpenCV contour detection for automatic layout generation
- **Layout Profiles** — Save, load, rename, and switch between venue configurations
- **Source Switching** — Toggle between Webcam, RTSP stream, and Video file demo modes
- **Live AI Analytics** — Historical trend analysis with in-memory snapshots
- **WebSocket Support** — Real-time updates via WebSocket (falls back to polling)
- **High-Performance Vision** — ROI-based detection and motion-skipping to minimize CPU load
- **Structured Logging** — Comprehensive logging system including SQLite history tracking
- **System Test Tool** — Comprehensive dependency and configuration validation

---

## 🏗️ Architecture

CrowdView AI is built on a modern, decoupled architecture:

```
React Frontend (Port 5173)
       ↕  HTTP + WebSocket
FastAPI Backend (Port 8000)
       ↓
VisionEngine (Background Thread)
  ├─ YOLOv8-Nano Model
  ├─ Webcam / RTSP / Video Capture
  └─ Area-Overlap + Temporal Logic
       ↓
Gemini 2.0 Flash API (OpenRouter)
  └─ AI Suggestions & Auto-Calibration
```

- **Vision Engine (Backend):** FastAPI server running YOLOv8-Nano via OpenCV. Ingests vision data every 7 seconds, processes the core Stability Logic, handles state transitions.
- **Digital Twin (Frontend):** React + Vite frontend rendering a 2D spatial map of the venue with live seat overlays.
- **Intelligence Layer:** Google Gemini 2.0 Flash turns raw spatial data into actionable operational advice.

### Project Structure

```
CrowdView AI/
├── backend/
│   ├── app.py                # FastAPI server and all endpoints
│   ├── vision_engine.py      # YOLOv8 detection loop and temporal logic
│   ├── models.py             # Pydantic data models
│   ├── logger_config.py      # Logging configuration
│   ├── db_logger.py          # SQLite analytics logger
│   ├── calibrate_seats.py    # Interactive seat calibration tool
│   └── test_system.py        # System test and validation tool
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Dashboard.jsx
│   │   ├── SeatGrid.jsx
│   │   ├── CameraOverlay.jsx
│   │   └── api.js
│   └── package.json
├── data/
│   ├── seating_map.json      # Seat coordinates and zones
│   ├── config.json           # Event configuration
│   └── layouts/              # Saved layout profiles
├── logs/                     # Log files (created automatically)
├── .env.example              # Environment variables template
└── requirements.txt
```

---

## 💻 Installation & Setup

### Prerequisites
- Python 3.8+ (Python 3.13 supported with updated Pydantic)
- Node.js 16+
- Webcam connected to your machine
- Gemini API key — get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

### 1. Clone the Repository
```bash
git clone https://github.com/Azimlearning/Crowed-View-AI.git
cd Crowed-View-AI
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

> **Python 3.13 note:** If you encounter issues with `pydantic-core`, try:
> ```bash
> pip install --only-binary :all: -r requirements.txt
> ```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. (Optional) Verify Setup
```bash
python backend/test_system.py
```
Checks all dependencies, camera access, YOLO model loading, and configuration files.

### 5. Running the Application

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python app.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` to view the dashboard.

---

## ⚙️ Configuration

### Seat Mapping (`data/seating_map.json`)

Defines seat coordinates in camera pixel space (640×480). Each seat has `id`, `x`, `y`, and `zone`. Use the interactive calibration tool instead of editing manually:

```bash
python backend/calibrate_seats.py
```

**Controls:**
- **LEFT CLICK** — Add seat at cursor position
- **DRAG** — Move existing seat
- **RIGHT CLICK** — Delete seat
- **1-9** — Change zone (1=VIP, 2=Standard, etc.)
- **S** — Save and exit
- **Q** — Quit without saving
- **C** — Clear all seats

> Space seats at least **2 × radius + 20px** apart. With the default radius of 65px, use ~150px spacing.

### Event Configuration (`data/config.json`)

| Parameter | Default | Description |
|---|---|---|
| `event_type` | `"Conference"` | Type of event |
| `zones` | — | Zone configs with empty thresholds |
| `detection_interval_seconds` | `7` | How often to run YOLO detection |
| `occupancy_overlap_threshold` | `0.6` | Required area overlap to count as occupied |
| `occupancy_confirmation_seconds` | `30` | Sustained overlap required to confirm occupancy |
| `vacancy_grace_period_minutes` | `20` | Minutes before marking an occupied seat empty |
| `person_detection_confidence_threshold` | `0.3` | YOLO confidence threshold |
| `debug_detection` | `false` | Show YOLO person bounding boxes in stream |
| `testing_mode` | `false` | Bypass temporal logic for instant updates |

> The system validates configuration on startup and warns about zone mismatches, out-of-bounds coordinates, and invalid thresholds.

---

## 🧠 How It Works

1. **Detection Loop** — Every 7 seconds, the system captures a frame and runs YOLOv8-Nano inference to detect persons (COCO class 0). ROI-based scanning and motion-skipping keep CPU usage low.

2. **Temporal Confirmation** — Each seat requires **60% area overlap sustained for 30 seconds** to transition Empty → Occupied. A **20-minute vacancy grace period** keeps seats marked Occupied after a person leaves, handling transient departures and preventing flickering.

3. **Actionable Flagging** — When a seat has been empty longer than its zone threshold (e.g., 10 min for VIP, 15 min for Standard), it becomes **Actionable (Orange)**.

4. **AI Suggestions** — Clicking an actionable seat sends zone statistics and event context to Gemini 2.0 Flash, which returns 3 categorized suggestions: **[Energy]** (HVAC, lighting) and **[Venue]** (space optimization, guest routing).

---

## 🖥️ Using the Dashboard

**Seat color codes:**
- 🟢 **Green** — Empty (seat available)
- 🔴 **Red** — Occupied (person confirmed)
- 🟠 **Orange** — Actionable (empty beyond threshold — click for AI suggestions)

**Zone Statistics** — Real-time per-zone metrics in the sidebar (total, occupied, empty, actionable %).

**Live Camera Feed** — MJPEG stream with drawn seat overlays. Includes a retry button if the connection drops.

**AI Suggestions Modal** — Click any orange seat to get Gemini-powered recommendations.

---

## 🔬 Testing & Debugging

### Debug Seat Map
Open `http://localhost:8000/api/debug-seat-map` in your browser to see a snapshot of the webcam with seat detection areas drawn. Use this to align seat coordinates with your physical setup.

- **Green circle** = Empty
- **Red circle** = Occupied
- **Orange circle** = Actionable

### Testing Occupancy
1. Open the debug seat map and note a seat position (e.g., `vip_1` at x=100, y=150).
2. Sit so your chest is inside that circle in the camera view.
3. Wait ~30 seconds (3 detection cycles). The seat should turn red on the dashboard.
4. If it doesn't, adjust the seat's `x`/`y` in `data/seating_map.json` and restart the backend.

### System Diagnostics
```bash
python backend/test_system.py
```
Verifies: Python dependencies, camera access, YOLO model loading, configuration validity, and API connectivity.

---

## 🛠️ Advanced Features

### Video File Mode (Simulation)
Use a video file instead of a live camera — ideal for demos:
```bash
# Add to .env:
VIDEO_FILE_PATH=path/to/your/video.mp4
```
The video loops automatically.

### Debug Mode
Enable YOLO bounding box visualization:
```json
// data/config.json
{ "debug_detection": true }
```
Person detections appear as cyan bounding boxes in the camera stream.

### RTSP Streams
Point to an IP camera via `.env`:
```bash
RTSP_URL=rtsp://username:password@192.168.1.100:554/stream
```

### Logging
Logs are saved to `logs/venue_ai_YYYYMMDD.log`. Adjust verbosity:
```bash
LOG_LEVEL=DEBUG  # DEBUG | INFO | WARNING | ERROR
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/seats` | Current status of all seats |
| `GET` | `/api/zones` | Zone-level statistics (cached 2s) |
| `GET` | `/api/debug-seat-map` | Webcam snapshot with seat circles |
| `GET` | `/api/camera-stream` | Live MJPEG stream with seat overlay |
| `POST` | `/api/suggestions` | AI suggestions for a zone (`{"zone_name": "VIP"}`) |
| `GET/POST` | `/api/config` | Read or hot-reload event configuration |
| `GET` | `/api/layouts` | List saved layout profiles |
| `POST` | `/api/auto-calibrate` | Auto-detect seats via Gemini or OpenCV |
| `POST` | `/api/analytics/insights` | AI-powered trend analysis |
| `WS` | `/ws/seats` | WebSocket for real-time seat updates |

---

## 🔧 Troubleshooting

**Webcam not opening:**
- Close apps using the camera (Teams, Zoom, browser tabs).
- Force a specific index: `CAMERA_INDEX=1` in `.env` (try 0, 1, 2).
- Use video file fallback: `VIDEO_FILE_PATH=...` in `.env`.

**YOLOv8 model download:**
- First run downloads ~6MB model — ensure internet is available.

**Configuration errors:**
- Run `python backend/test_system.py`.
- Ensure zone names in `seating_map.json` match `config.json`.
- Ensure seat coordinates are within 0–640 (x) and 0–480 (y).

**Gemini API errors:**
- Verify `GEMINI_API_KEY` in `.env`.
- Check quota at Google AI Studio.
- Check `logs/` for detailed error messages.

**Frontend not connecting:**
- Ensure backend is running on port 8000.
- Check browser console for CORS errors.
- Verify proxy settings in `vite.config.js`.

---

## ⚡ Performance Notes

- **CPU Usage** — YOLOv8-Nano is optimized for CPU but requires moderate processing power.
- **Detection Interval** — 7 seconds balances responsiveness with CPU load.
- **Motion Skip** — YOLO is skipped on static frames (forced every 30s) to reduce overhead.
- **ROI Detection** — Only seat areas are scanned, not the full frame.
- **Zone Cache** — Zone statistics cached for 2 seconds to reduce computation.

---

## 🤝 Philosophy

We do not believe in removing humans from the loop. CrowdView AI advises and filters the chaos, dramatically reducing the cognitive load on stage managers — but the decision, the final execution, always remains in the hands of a human operator.

**CrowdView AI converts a reactive security team into a proactive, perfectly choreographed orchestra.**

---

## Known Limitations (TRL 3)

- Single webcam support only (no multi-camera fusion)
- Seat coordinates hardcoded to 640×480 resolution
- No historical data persistence (in-memory state only)
- No API authentication or rate limiting
- Local deployment only (no cloud/distributed architecture)

## Future Enhancements

- Multiple camera support with frame fusion
- Adaptive resolution scaling
- Database persistence layer
- API authentication & rate limiting
- Cloud deployment readiness
- Comprehensive unit/integration test suite

---

<div align="center">
  <i>Developed for UTP Pitch Presentation &nbsp;•&nbsp; TRL 3 Prototype &nbsp;•&nbsp; Version 1.0</i>
</div>
