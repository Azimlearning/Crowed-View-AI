# Design: Dynamic Seat Placement (Camera Overlay)

## Context
The CrowdView AI prototype currently displays seat occupancy data on a secondary dashboard using a standard CSS abstract flex/grid layout. While functional, it does not spatially correlate to the real-world venue, reducing the intuitive value of the dashboard.

## Objective
Implement a "Camera Overlay" view that superimposes seat status and actionable insights directly over the live camera feed, drastically improving spatial awareness while retaining the existing abstract grid as an alternative toggleable view.

## Constraints & Requirements
- **TRL 3 Prototype:** Must be implemented quickly using existing backend capabilities.
- **Backend Stability:** No changes to the backend mapping or API logic; use the existing `/api/camera-stream` and pixel coordinates from `/api/seats`.
- **Fallbacks:** The original `SeatGrid` must remain accessible via a toggle button.

## Architecture & Data Flow

### 1. Backend Integration (Unchanged)
The frontend already consumes two critical endpoints:
1. `GET /api/camera-stream`: An MJPEG stream of the active camera.
2. `GET /api/seats` (and WebSocket `/ws/seats`): Provides an array of `Seat` objects containing:
   - `id`, `status`, `zone`, `overlap_percentage`, `is_actionable`
   - **Crucially:** `x`, `y`, `width`, `height` (absolute pixel coordinates from the original 640x480 frame).

### 2. Frontend Component (`CameraOverlay.jsx`)
A new React component will be created to handle the overlay logic.
- **Rendering the Stream:** The component will render a `<img src="http://localhost:8000/api/camera-stream" />` as the base layer.
- **Dynamic Coordinate Routing:**
  - The native video feed from the backend is 640x480.
  - The frontend `<img>` might be responsive (e.g., taking up 100% width of its container).
  - The overlay component must use a `ResizeObserver` or stateful tracking of the `<img>`'s rendered `clientWidth` and `clientHeight` to compute scaling factors:
    `scaleX = currentImgWidth / 640`
    `scaleY = currentImgHeight / 480`
  - Seat bounding boxes will be rendered as absolutely positioned `div` elements over the image using the scaled coordinates.

### 3. UI/UX Details
- **Seat Visualization:**
  - **Occupied:** Semi-transparent Red border/fill (`rgba(244, 67, 54, 0.4)`).
  - **Empty:** Semi-transparent Grey border/fill (`rgba(158, 158, 158, 0.2)`).
  - **Actionable (Empty for > Threshold):** Semi-transparent Orange border/pulse (`rgba(255, 152, 0, 0.6)`).
- **Interactivity:**
  - Standard CSS `hover` states to brighten the box.
  - Re-use the existing tooltip logic (showing ID, grace period, AI suggestions prompt).
  - Clicking an actionable seat triggers the exact same `onSeatClick` handler that opens the AI suggestions modal.
- **View Toggle (`Dashboard.jsx`):**
  - Add a state variable `viewMode` (`'grid'` | `'camera'`).
  - Add a toggle button group (e.g., "Abstract Grid" | "Live Map") above the seating area.

## Future Phases (Out of Scope for this PR)
- Phase 2: Drag-and-drop abstract canvas builder for arbitrary logical groups.
- Phase 3: 2D floor plan homography mapping.
