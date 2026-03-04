# Findings

## Research
- YOLOv8-Nano operates on class 0 (person) from COCO dataset at 0.3 confidence threshold
- Area-based overlap is more robust than circle-center distance for top-down CCTV angles
- Cumulative overlap (multiple people contributing to one seat) handles crowded scenarios

## Discoveries
- Old system: circle overlap + stability counter (3 scans × 7s = 21s delay)
- New system: rectangle overlap ≥60% + 30s confirmation + 20-min vacancy grace period
- Testing mode bypasses both timers for instant demo updates
- `_compute_rect_intersection_area()` uses axis-aligned rectangle intersection (max/min clamp)
- Cumulative overlap can exceed 100% when multiple bboxes overlap the same seat pixels — capped at 1.0

## Constraints
- Camera resolution fixed at 640×480
- Seat coordinates are in camera pixel space (top-left corner of rectangle)
- Default seat size 100×100 pixels (~1/30th of frame)
- Vacancy grace period is applied per-seat, not per-zone
- `seating_map.json` must include `width` and `height` per seat (defaults to 100 if absent)
