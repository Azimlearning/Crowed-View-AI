# Design: Drag-and-Drop Abstract Grid Builder

## Context
The CrowdView AI prototype currently relies on a CSS flex/grid to automatically wrap the "Abstract Grid" seat elements sequentially. While the newly added Camera Overlay provides exact real-world spatial mapping, many venues prefer an abstract top-down visual hierarchy (e.g., grouped by tables of 4, rows of 10) rather than a rigid perspective.

## Objective
Implement an interactive drag-and-drop grid builder on the frontend. This will allow the user to manually position seats on a logical canvas and save that visual grouping without altering the backend's camera bounding-box coordinates.

## Constraints & Requirements
- **No Backend Modifications:** The backend `seating_map.json` MUST remain the source of truth for the AI vision system's physical bounding boxes.
- **Frontend Persistence:** We must persist the user's custom logical layout in the browser's `localStorage`.
- **Fallbacks:** Must cleanly handle new seats added by the backend that haven't been placed manually yet.

## Architecture

### 1. The `SeatGrid` Component Overhaul
The `SeatGrid.jsx` will be migrated from a static CSS layout (`grid-template-columns`) to a relative/absolute canvas system where seats are absolutely positioned relative to the zone container.

### 2. "Edit Layout" Mode
- **State Toggle:** Add a `isEditingLayout` boolean state to the dashboard.
- **Interactivity:**
  - When `false`, seats are static but still clickable for AI suggestions.
  - When `true`, seats become draggable HTML elements (using standard mouse/touch event tracking or a lightweight library-free implementation).

### 3. State Management & `localStorage`
- **Data Structure:**
  ```javascript
  // localStorage key: 'crowdview_layout_v1'
  {
    "Seat-A1": { x: 100, y: 50 },
    "Seat-A2": { x: 250, y: 50 }
  }
  ```
- **Fallback Logic:** If a seat exists in the backend API response but is NOT found in the `localStorage` layout mapping, it will be placed in a default "Unassigned" row at the top or bottom of the canvas, ensuring it is never hidden from the user.

### 4. UI/UX Details
- A **"Save Layout"** and **"Discard Changes"** action bar will appear when in Edit Mode.
- A **"Reset to Default"** button will clear the `localStorage` key, reverting the view back into a standard auto-flowing grid or a packed layout.
- The drag interaction will show visual feedback (changing cursor, higher z-index, slight opacity drop while dragging).

## Trade-offs Accepted
- Relying on `localStorage` means the custom layout is browser-specific. If the user loads the dashboard on their phone, they will see the default layout unless they build a new one. This is highly acceptable for a TRL 3 hackathon prototype where speed and zero-backend-dependency is prioritized.
