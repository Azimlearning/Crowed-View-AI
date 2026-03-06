# Design: Live Camera Seat Calibration

## Context
The previous "Drag-and-Drop Abstract Grid" (Phase 2) was designed as a frontend-only visual abstraction. However, the user clarified a desire to visually configure the *actual* AI bounding boxes directly through the dashboard, including adding/removing/moving seats, and having those changes instantly affect the live detection logic.

## Objective
Convert `CameraOverlay.jsx` into an interactive calibration tool when `isEditingLayout` is enabled, and build backend capabilities to accept, save, and hot-reload these physical AI bounding boxes.

## Architecture & Data Flow

### 1. Backend: Hot-Reloading Vision Engine
- **`vision_engine.py`**: Add a `reload_seating_map()` method that acquires the thread lock, clears current seat mappings, re-reads `data/seating_map.json`, and re-computes the detection ROI (`_compute_detection_roi()`).
- **`app.py`**: Add a new `POST /api/seating-map` endpoint. It will:
  1. Accept a complete JSON payload matching the structure of `seating_map.json`.
  2. Validate the data (e.g., ensure bounds are within 640x480).
  3. Overwrite `data/seating_map.json` securely.
  4. Invoke `vision_engine.reload_seating_map()`.

### 2. Frontend: Interactive Camera Overlay
- **Component**: `CameraOverlay.jsx` will intercept mouse events.
- **Drag & Drop**: When `isEditingLayout` is true, the user can click and drag the actual colored bounding boxes over the live video stream.
  - Using the inverse of the resize scale (`1 / scale.x`, `1 / scale.y`), we map the screen mouse delta back to the raw 640x480 coordinate space.
- **Add/Remove Seats**: 
  - Add a "Add Seat" button to the control bar. It drops a default 100x100 box in the center of the camera view, generating a unique ID (e.g., `Seat-New-1`).
  - Add a "Delete" button or a small 'x' on the active dragged seat to remove it from the array.
- **Save Strategy**: 
  - Clicking "Save Layout" will construct the backend-expected JSON payload (grouping by `zone`) and fire the POST request.
  - The dashboard will then resume polling, seamlessly seeing the AI's detection updates on the newly drawn boxes.

## Dependencies & Risks
- **Concurrency**: `VisionEngine.lock` must be carefully utilized to prevent YOLO from running on half-loaded seat data.
- **Data Shape**: The frontend needs to ensure any new seat is assigned to a valid `zone` (prompting the user or defaulting to the first available zone).
