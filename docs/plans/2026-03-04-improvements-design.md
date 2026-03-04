# CrowdView AI Feature Improvements Design

**Goal:** Implement visual synchronization for new detection logic (rectangles/timers), a testing bypass mode, and enhance the Gemini AI operations—all while maintaining the strict local-only, TRL 3 prototype constraints.

## Architecture & Phasing
We will split this into two phases to ensure the visual foundation is correct before touching the intelligence layer. This prevents regressions in the core tracking loop.

### Phase 1: The Visual Truth & Demo Prep
**1. Rectangular Seat Render**
We will update `SeatGrid.jsx` to parse `width` and `height` from the seat data currently provided by the backend (or fallback to defaults) and render accurate rectangles instead of circles, mapping 1:1 with the OpenCV calibration tool.
- *Constraint Check:* Keeps processing lightweight on the client.

**2. Visualizing Time**
We need to communicate the unseen backend logic:
- **30s Stability:** Add a CSS pulsing effect (e.g., yellow border) when a seat is currently detected as occupied but hasn't reached the 30s threshold. 
- **20m Grace Period:** Display a string (like "18m left") on newly empty seats counting down until they hit the Actionable (Orange) state.
- *Constraint Check:* Purely frontend visual; no extra DB needed.

**3. "Testing Mode" Toggle**
For live demos, waiting 20 minutes is impossible. 
- Add a toggle in the dashboard sidebar.
- Toggling it calls `PUT /api/config` to set `testing_mode: true`. 
- The backend `VisionEngine` checks this flag; if true, the `empty_threshold_minutes` is effectively forced to 0.

### Phase 2: Analytics & Intelligence (Pending UI Approval)
**4. Session Analytics**
- We will add a simple, session-only chart (e.g., using a lightweight charting library or simple HTML/CSS bars) to the React dashboard showing the current ratio of occupied vs empty seats over the last hour.
- *Constraint Check:* Strict adherence to "No DB". All stats are kept in React memory (or Python RAM) and die when the app restarts.

**5. Gemini Context Enhancement**
- Currently, suggestions might be generic. We will update the `app.py` prompt to include the newly visible "grace period" data and the exact duration a seat has been actionable, asking Gemini to prioritize immediate revenue recovery (e.g., "Seat VIP-1 has been empty for exactly 22 minutes").

---
## Verification Plan
1. **Calibration Sync:** Manually adjust a seat rectangle in the backend calibration tool and verify it mirrors perfectly in the React UI.
2. **Timer Tests:** Physically sit in a seat's region, verify the yellow pulse for ~30s before turning red. 
3. **Demo Mode Test:** Hit the "Testing Mode" toggle and vacating a seat. It should immediately hit the Orange/Actionable state.
4. **AI Generation:** Click the Orange seat and ensure the Gemini prompt output includes specific timing data.
