# Feature Improvements Implementation Plan

> **Note to Executor:** Execute this plan task-by-task using the `executing-plans` skill, following testing and verification steps exactly.

**Goal:** Implement visual synchronization for new detection logic (timers/rectangles) and enhance the Gemini AI operations while maintaining the TRL 3 prototype constraints.

**Architecture:** We will pass the backend config to the React frontend to compute real-time visual states (30s confirmation pulse, 20m grace period countdown). We'll also add a lightweight, dependency-free React analytics bar and update the Gemini prompt in the FastAPI backend to use the new temporal context.

**Tech Stack:** React (Vite), CSS, Python (FastAPI), Gemini API.

---

### Task 1: Expose Configuration to SeatGrid

**Files:**
- Modify: `frontend/src/Dashboard.jsx`

**Step 1: Check existing `Dashboard.jsx`**
Run: `cat frontend/src/Dashboard.jsx | grep 'const \[testingMode'`
Expected: `const [testingMode, setTestingMode] = useState(false);`

**Step 2: Write minimal implementation**
Update `frontend/src/Dashboard.jsx` to store the full config object so we can pass threshold integers to child components. Add `const [config, setConfig] = useState(null);` in state. In `loadConfig()`:
```javascript
        const cfg = await getConfig();
        setConfig(cfg);
        setTestingMode(cfg.testing_mode || false);
        setConfigLoaded(true);
```
Pass the `config={config}` prop to `<SeatGrid seats={seats} onSeatClick={handleSeatClick} config={config} />`.

**Step 3: Run test to verify it compiles**
Run: `cd frontend && npm run build`
Expected: Successful build with no critical errors.

**Step 4: Commit**
```bash
git add frontend/src/Dashboard.jsx
git commit -m "feat(ui): expose backend config to SeatGrid for timer rendering"
```

---

### Task 2: Visualize Time & Aspect Ratio in SeatGrid

**Files:**
- Modify: `frontend/src/SeatGrid.jsx`

**Step 1: Add time and detection logic to seat render**
Modify `getSeatColor` and the card renderer in `SeatGrid.jsx`. 
Extract the config thresholds:
```javascript
  const overlapThreshold = config?.occupancy_overlap_threshold || 0.6;
  const isDetecting = seat.status === 'Empty' && seat.overlap_percentage >= overlapThreshold;
```
If `seat.vacancy_timer_start` exists, calculate remaining minutes (using `config.vacancy_grace_period_minutes`).
Add the `detecting` class if `isDetecting` is true. Render the actual `width` and `height` dynamically as aspect ratios `aspectRatio: seat.width / seat.height`. Add a text span showing `-XXm` if the grace period is active.

**Step 2: Check formatting**
Ensure the JSX doesn't break. Verify tooltip string includes the new states.

**Step 3: Run test to verify it compiles**
Run: `cd frontend && npm run build`
Expected: Successful build.

**Step 4: Commit**
```bash
git add frontend/src/SeatGrid.jsx
git commit -m "feat(ui): add 30s detection and 20m grace period visual states"
```

---

### Task 3: Add CSS for Visual Pulses

**Files:**
- Modify: `frontend/src/SeatGrid.css`

**Step 1: Write CSS animations**
Add styles for `.seat.detecting` to outline it with a pulsing yellow shadow to represent the 30-second temporal confirmation period.
```css
.seat.detecting {
  border: 2px solid #ffeb3b;
  animation: pulse-detecting 1.5s infinite;
}

@keyframes pulse-detecting {
  0% { box-shadow: 0 0 0 0 rgba(255, 235, 59, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(255, 235, 59, 0); }
  100% { box-shadow: 0 0 0 0 rgba(255, 235, 59, 0); }
}
```

**Step 2: Commit**
```bash
git add frontend/src/SeatGrid.css
git commit -m "style: add yellow pulse animation for detection confirmation"
```

---

### Task 4: Simple Session Analytics UX

**Files:**
- Modify: `frontend/src/Dashboard.jsx`

**Step 1: Render an inline HTML/CSS progress bar**
In `Dashboard.jsx`, above the `live-camera-section`, add a new `div className="analytics-section"` that sums all `occupied_seats`, `empty_seats`, and `actionable_seats` from the `zones` array and displays a horizontal stacked bar using standard inline flex formatting (e.g., width `%` corresponding to the ratios). This uses NO external libraries to respect the memory/budget constraints of TRL 3.

**Step 2: Build and Test UI visually**
Run: `cd frontend && npm run build`
Expected: Successful build.

**Step 3: Commit**
```bash
git add frontend/src/Dashboard.jsx
git commit -m "feat(ui): add simple stacked bar chart for session analytics"
```

---

### Task 5: Enhance Gemini AI Prompt Context

**Files:**
- Modify: `backend/app.py`

**Step 1: Check existing prompt**
Run: `findstr /N "Generate suggestions using Gemini API" backend\app.py`
Expected: Confirm line number location for prompt construction.

**Step 2: Write enhanced prompt**
Update the `/api/suggestions` endpoint in `app.py`. Modify the prompt string to explicitly mention revenue recovery and the specific grace periods observed. 
```python
        prompt = (
            f"The event is a {event_type}. In the {request.zone_name} zone, "
            f"{empty_percentage:.1f}% of seats are Empty. "
            f"These seats have exceeded the {zone.empty_threshold_minutes}-minute threshold and have been empty for an average of {avg_empty_duration:.1f} minutes. "
            f"Given our goal to maximize venue optics and recover lost ticketing revenue without moving physical seats, "
            f"provide 2-3 specific, actionable operational suggestions (e.g., offering seat upgrades to waiting list guests, moving back-row attendees forward). "
            f"Format your response as a simple list, one suggestion per line."
        )
```

**Step 3: Test backend syntax**
Run: `python -m py_compile backend/app.py`
Expected: No syntax errors.

**Step 4: Commit**
```bash
git add backend/app.py
git commit -m "feat(api): enhance gemini prompt with revenue recovery and exact temporal context"
```

---
**Verification**: 
Run `python backend/test_system.py` to ensure core integrations weren't broken. Restart backend and frontend, and click toggle testing mode manually inside the browser.
