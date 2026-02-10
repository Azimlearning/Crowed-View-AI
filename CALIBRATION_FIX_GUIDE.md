# CrowdView AI - Calibration Fix Guide

## Problem

Detection is working (YOLO sees people), but seat circles are often **mispositioned** relative to where people actually sit. Example:

- Person detection box: `[0, 174, 312, 479]` (center ~156, 326)
- Seat std_3 in config: `(400, 300)`
- Distance from box to seat center: **88px** > radius 65px → **no overlap**, so the seat stays Empty.

So the seat circle is drawn too far (e.g. to the right) from where the camera actually sees you.

---

## Quick fix 1: Increase detection radius

In `data/config.json` set a larger radius so current positions still overlap:

```json
{
  "seat_detection_radius_pixels": 100
}
```

(Overlap validation is warning-only, so the app will start even if circles overlap.)

Then **restart the backend**: `python backend/app.py` (or `python app.py` from `backend/`).

---

## Quick fix 2: Recalibrate seat positions

Use the calibration tool so circles match where people sit:

```bash
python backend/calibrate_seats.py
```

- Left-click to add a seat, drag to move, right-click to remove.
- Position each circle where a person’s torso/center would be in the camera view.
- Press **S** to save to `data/seating_map.json`.

---

## Using the overlap debugger

1. Start the backend and open:  
   **http://localhost:8000/api/debug-detection-status**
2. Save the JSON to **`debug_status.json`** in the project root.
3. Run:

   ```bash
   python backend/debug_overlap.py
   ```

The script will:

- Print for each seat whether each detection overlaps (and distance/margin).
- Suggest a **required radius** if there’s no overlap (e.g. “Need radius >= 93px”).
- Optionally write **`overlap_diagram.png`** (640×480) showing detection boxes and seat circles (green = overlapping, red = not).

Use that to decide whether to increase `seat_detection_radius_pixels` or to move seats with the calibration tool.

---

## Optional: Get detection center and edit seating_map.json

From the debug endpoint, `last_person_detections` is a list of `[x1, y1, x2, y2]`. Center of one detection:

- center_x = (x1 + x2) / 2  
- center_y = (y1 + y2) / 2  

Put seat coordinates in `data/seating_map.json` near those centers (and space seats so circles don’t overlap too much). Then restart the backend.

---

## Summary

| Issue | Action |
|-------|--------|
| Seats never turn Occupied | Increase radius and/or run `calibrate_seats.py` so circles sit where people are. |
| See why a seat doesn’t overlap | Save `/api/debug-detection-status` as `debug_status.json`, run `python backend/debug_overlap.py`. |
| Circles in wrong place | Run `python backend/calibrate_seats.py` and reposition. |
