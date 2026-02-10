# Venue Intelligence AI - TRL 3 Prototype

A proof-of-concept system that uses YOLOv8-Nano to detect seat occupancy via webcam and provides AI-generated operational suggestions for empty seats using Google's Gemini API.

## Features

- **Real-time Seat Detection**: Uses YOLOv8-Nano (optimized for CPU) to detect person occupancy
- **Stability Counter**: Prevents flickering by requiring 3 consecutive identical scans before status change
- **Time Tracking**: Flags seats as "actionable" when empty for longer than zone-specific thresholds
- **AI Suggestions**: Integration with Gemini 1.5 Flash API for operational recommendations
- **2D Digital Twin Dashboard**: React-based visualization showing seat status in real-time
- **Interactive Seat Calibration Tool**: Click-to-place seat mapping with visual feedback
- **System Test Tool**: Comprehensive dependency and configuration validation
- **Video File Fallback**: Use video files instead of live camera for demos
- **WebSocket Support**: Real-time updates via WebSocket (optional, falls back to polling)
- **Enhanced Error Handling**: Retry logic, user-friendly error messages, and graceful degradation
- **Debug Visualization**: Person detection bounding boxes when debug mode enabled
- **Structured Logging**: Comprehensive logging system with file and console output

## Project Structure

```
CrowdView AI/
├── backend/              # Python FastAPI backend
│   ├── app.py           # FastAPI server and endpoints
│   ├── vision_engine.py # YOLOv8 detection loop
│   ├── models.py        # Pydantic data models
│   ├── logger_config.py # Logging configuration
│   ├── calibrate_seats.py # Interactive seat calibration tool
│   └── test_system.py   # System test and validation tool
├── frontend/            # React dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Dashboard.jsx
│   │   ├── SeatGrid.jsx
│   │   └── api.js
│   └── package.json
├── data/
│   ├── seating_map.json # Seat coordinates and zones
│   └── config.json     # Event configuration
├── logs/                # Log files (created automatically)
├── .env.example        # Environment variables template
└── requirements.txt
```

## Prerequisites

- Python 3.8+ (Python 3.13 supported with updated Pydantic version)
- Node.js 16+
- Webcam connected to your laptop
- Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

## Installation

### Backend Setup

1. Create a virtual environment (recommended):
```powershell
python -m venv venv
# Activate the virtual environment:
.\venv\Scripts\activate
```

2. Install Python dependencies:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** If you encounter issues with `pydantic-core` on Python 3.13, the requirements.txt uses `pydantic>=2.9.0` which should have better Python 3.13 support. If problems persist, try installing with pre-built wheels only:
```powershell
pip install --only-binary :all: -r requirements.txt
```

3. Create a `.env` file in the project root:
```bash
cp .env.example .env
```

4. Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_actual_api_key_here
```

5. (Optional) Test your system setup:
```bash
python backend/test_system.py
```

This will verify all dependencies, camera access, model loading, and configuration files.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

## Configuration

### Seat Mapping (`data/seating_map.json`)

Define seat coordinates in camera pixel space. Each seat has:
- `id`: Unique identifier
- `x`, `y`: Pixel coordinates in the camera frame
- `zone`: Zone name (must match config.json)

**Seat spacing:** To avoid overlapping circles, space seat centers at least **2 × radius + 20px** apart. For example, with radius 65px (default), use ~150px spacing (e.g., x = 100, 250, 400, ...).

#### Using the Calibration Tool

Instead of manually editing JSON files, use the interactive calibration tool:

```bash
python backend/calibrate_seats.py
```

**Controls:**
- **LEFT CLICK**: Add seat at cursor position
- **DRAG**: Move existing seat
- **RIGHT CLICK**: Delete seat
- **1-9**: Change zone (1=VIP, 2=Standard, etc.)
- **S**: Save and exit
- **Q**: Quit without saving
- **C**: Clear all seats

The tool shows detection radius circles and automatically saves to `data/seating_map.json`.

### Event Configuration (`data/config.json`)

- `event_type`: Type of event (e.g., "Conference", "Concert")
- `zones`: Zone configurations with empty thresholds
- `detection_interval_seconds`: How often to run detection (default: 7)
- `stability_required_scans`: Consecutive scans needed for status change (default: 3)
- `seat_detection_radius_pixels`: Radius around seat to check for persons (default: 65)
- `person_detection_confidence_threshold`: YOLO confidence threshold (default: 0.3)
- `debug_detection`: Enable debug mode to show person bounding boxes (default: false)

**Note:** The system validates configuration on startup and will warn about:
- Zone name mismatches between config.json and seating_map.json
- Seat coordinates outside camera bounds (0-640, 0-480)
- Overlapping detection radii
- Invalid threshold values

## Usage

### 1. Calibrate Seats (First Time Setup)

Before running the system, map your seats:

```bash
python backend/calibrate_seats.py
```

Use the interactive tool to place seats at their actual positions in the camera view.

### 2. Start the Backend

From the project root directory:
```bash
cd backend
python app.py
```

Or using uvicorn directly:
```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

The backend will:
- Load the YOLOv8-Nano model (first run downloads ~6MB model)
- Validate configuration files
- Start the webcam detection loop
- Serve API endpoints on `http://localhost:8000`
- Create log files in `logs/` directory

### 2. Start the Frontend

In a new terminal, from the project root:
```bash
cd frontend
npm run dev
```

The dashboard will open at `http://localhost:5173`

### 3. Using the Dashboard

- **Seat Status**: Seats are color-coded:
  - 🟢 Green: Empty (seat available)
  - 🔴 Red: Occupied (seat taken, person detected)
  - 🟠 Orange: Actionable (empty for threshold duration)
  
- **Zone Statistics**: View real-time statistics for each zone in the sidebar (cached for performance)

- **AI Suggestions**: Click on an actionable (orange) seat to get AI-generated operational suggestions

- **Live Camera Feed**: Real-time camera stream with seat overlay. Includes retry button if connection fails.

- **Improved Seat Grid**: Responsive grid layout with hover tooltips showing detailed seat information

## Testing Seat Detection and Camera

### 1. See where the camera thinks seats are

Open in your browser:

**http://localhost:8000/api/debug-seat-map**

You get a snapshot of the webcam with circles drawn at each seat. The circle is the **detection radius** (65 px by default, configurable in `data/config.json`). A person's bounding box must overlap this circle for the seat to count as occupied. **Green circle** = seat empty, **Red circle** = seat occupied.

- **Green circle** = seat currently Empty  
- **Red circle** = Occupied  
- **Orange circle** = Actionable (empty for threshold duration)

Use this to align yourself (or a test person) with a seat.

### 2. Camera and coordinate system

- Resolution is **640×480** (see `vision_engine.py`). Seat coordinates in `data/seating_map.json` are in these pixel coordinates.
- **VIP seats** in the sample map: roughly a row at y≈150, x = 100, 200, 300.
- **Standard seats**: row at y≈300, x = 100, 200, 300, 400, 500.
- A seat is **occupied** when a person's bounding box (from YOLO) overlaps the detection circle (65 pixels radius by default) around the seat (x, y).

### 3. Test “occupied” (seat turns green)

1. Open the debug image (step 1) and note one seat circle (e.g. `vip_1` at (100, 150)).
2. Sit or stand so your **chest/center** is inside that circle in the camera view.
3. Wait for **3 detection cycles** (about **21 seconds** with a 7 s interval). The seat should turn **green** on the dashboard.
4. If it doesn’t, move closer to the circle center or adjust `data/seating_map.json` so that seat’s (x, y) matches your layout, then restart the backend.

### 4. Test stability (no flicker)

- Walk quickly past a seat (don’t stay in the circle). The seat should **not** flip to occupied; it only changes after 3 consecutive scans with the same result.

### 5. Test “actionable” and AI suggestions

- Leave a seat **empty** (nobody in its circle) for longer than the zone threshold (e.g. **10 minutes** for VIP, **15 minutes** for Standard in `data/config.json`).
- That seat should turn **orange** on the dashboard.
- **Click the orange seat** to request AI suggestions; the modal should show 2–3 suggestions from the Gemini API.

### 6. Adjust seat positions

If the circles in the debug image don’t match your room:

1. Edit `data/seating_map.json`: change each seat’s `x` and `y` (0–640 and 0–480).
2. Optionally change `seat_detection_radius_pixels` in `data/config.json` (default 65). If you increase the radius, also increase seat spacing in `seating_map.json` to avoid overlap.
3. Restart the backend and reload the debug image and dashboard.

## API Endpoints

- `GET /api/seats` - Get current status of all seats
- `GET /api/zones` - Get zone-level statistics (cached for 2 seconds)
- `GET /api/debug-seat-map` - Snapshot of webcam with seat circles drawn (for testing)
- `GET /api/camera-stream` - Live MJPEG stream of camera with seat overlay
- `POST /api/suggestions` - Get AI suggestions for a zone
  ```json
  {
    "zone_name": "VIP"
  }
  ```
- `WS /ws/seats` - WebSocket endpoint for real-time seat updates (optional, falls back to polling)

## How It Works

1. **Detection Loop**: Every 7 seconds (configurable), the system:
   - Captures a frame from the webcam
   - Runs YOLOv8-Nano inference to detect persons (class 0)
   - Checks if any person is within the detection radius of each seat

2. **Stability Logic**: 
   - Each seat maintains a stability counter
   - Status only changes after 3 consecutive scans show the same result
   - Prevents flickering from people walking past

3. **Time Tracking**:
   - When a seat becomes empty, `last_empty_time` is recorded
   - If empty duration exceeds the zone threshold, `is_actionable` is set to true

4. **AI Suggestions**:
   - When a user clicks an actionable seat, the backend:
     - Calculates zone statistics
     - Sends a prompt to Gemini API with event context
     - Returns 2-3 professional suggestions

## Advanced Features

### Video File Mode

Instead of using a live camera, you can use a video file for demos or testing:

1. Add to `.env`:
   ```bash
   VIDEO_FILE_PATH=path/to/your/video.mp4
   ```

2. The system will automatically use the video file if the camera is unavailable or if `VIDEO_FILE_PATH` is set.

3. The video will loop automatically when it reaches the end.

### Debug Mode

Enable debug visualization to see person detection bounding boxes:

1. Edit `data/config.json`:
   ```json
   {
     "debug_detection": true
   }
   ```

2. Restart the backend. Person detections will now show as cyan bounding boxes in the camera stream.

### Logging

Logs are automatically saved to `logs/venue_ai_YYYYMMDD.log`. Set log level via environment variable:

```bash
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

## Troubleshooting

### Webcam Not Opening / Not Connected
- **Close other apps** that might use the camera (Teams, Zoom, browser tabs, other dev tools).
- The app tries **index 0, then 1, then 2** and on Windows uses **DirectShow** first. Check logs for camera status.
- **Force a specific camera:** In your project root `.env` add:
  ```bash
  CAMERA_INDEX=1
  ```
  (Try `0`, `1`, or `2` if you have multiple cameras.) Restart the backend.
- **Use video file fallback:** Set `VIDEO_FILE_PATH` in `.env` to use a video file instead.
- If the feed is black: same camera may be in use elsewhere, or try another index via `CAMERA_INDEX`.

### YOLOv8 Model Download
- First run will download the model (~6MB)
- Ensure internet connection for initial download

### Configuration Validation Errors
- Run `python backend/test_system.py` to check for configuration issues
- Ensure zone names in `seating_map.json` match `config.json`
- Check that seat coordinates are within 0-640 (x) and 0-480 (y)
- Verify detection radii don't overlap (system will warn you)

### Gemini API Errors
- Verify your API key is set in `.env`
- Check API quota/limits at Google AI Studio
- Check logs in `logs/` directory for detailed error messages

### Frontend Not Connecting
- Ensure backend is running on port 8000
- Check browser console for CORS errors
- Verify proxy settings in `vite.config.js`
- Use the "Retry Connection" button if camera stream fails

### System Test Tool
Run comprehensive system diagnostics:
```bash
python backend/test_system.py
```

This checks:
- All Python dependencies
- Camera access
- YOLO model loading
- Configuration file validity
- Vision engine initialization
- API connectivity (if backend is running)

## Performance Notes

- **CPU Usage**: YOLOv8-Nano is optimized for CPU but still requires moderate processing power
- **Detection Interval**: 7 seconds balances responsiveness with CPU usage
- **Stability Counter**: 3 scans prevents false positives but adds ~21 seconds delay to status changes

## Limitations (TRL 3 Prototype)

- Single webcam support only
- Predefined seat coordinates (no automatic calibration)
- No facial recognition (person detection only)
- No historical data persistence
- Runs locally only (no cloud deployment)

## Future Enhancements

- Multiple camera support
- Automatic seat mapping/calibration
- Historical analytics dashboard
- WebSocket for real-time updates (instead of polling)
- Database persistence
- Multi-event support

## License

This is a proof-of-concept prototype for research/development purposes.
