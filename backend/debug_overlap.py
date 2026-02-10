"""
CrowdView AI - Overlap debugger.

Analyzes why seats are or aren't detecting. Reads JSON from
GET /api/debug-detection-status (save as debug_status.json), then reports
overlap yes/no, distance, and required radius or repositioning hints.

Usage:
  1. With backend running: open http://localhost:8000/api/debug-detection-status
  2. Save the JSON to debug_status.json (same directory as this script or project root)
  3. Run: python backend/debug_overlap.py
"""
import json
import sys
from pathlib import Path
from math import sqrt


def _box_overlaps_circle(x1: int, y1: int, x2: int, y2: int, cx: int, cy: int, radius: int) -> bool:
    """Check if bounding box (x1,y1,x2,y2) overlaps circle at (cx,cy) with radius."""
    nearest_x = max(x1, min(cx, x2))
    nearest_y = max(y1, min(cy, y2))
    distance = sqrt((nearest_x - cx) ** 2 + (nearest_y - cy) ** 2)
    return distance <= radius


def _distance_box_to_point(x1: int, y1: int, x2: int, y2: int, px: int, py: int) -> float:
    """Distance from point (px,py) to nearest point on box."""
    nearest_x = max(x1, min(px, x2))
    nearest_y = max(y1, min(py, y2))
    return sqrt((nearest_x - px) ** 2 + (nearest_y - py) ** 2)


def analyze_overlap(debug_json_path: str) -> None:
    """Analyze debug status JSON and print overlap analysis."""
    path = Path(debug_json_path)
    if not path.exists():
        print(f"File not found: {path}")
        print("Save http://localhost:8000/api/debug-detection-status to debug_status.json")
        return

    with open(path, "r") as f:
        data = json.load(f)

    seats = data.get("seats", [])
    detections = data.get("last_person_detections") or []
    config = data.get("config", {})
    radius = config.get("seat_detection_radius_pixels", 65)

    print("\n" + "=" * 60)
    print("CROWDVIEW AI - DETECTION OVERLAP ANALYZER")
    print("=" * 60 + "\n")
    print(f"Config: radius={radius}px, stability_scans={config.get('stability_required_scans', 3)}")
    print(f"Detections: {len(detections)}")
    if detections:
        for i, d in enumerate(detections):
            if len(d) >= 4:
                x1, y1, x2, y2 = d[0], d[1], d[2], d[3]
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                print(f"  Detection {i+1}: box [{x1},{y1},{x2},{y2}] center=({cx},{cy})")
    print()

    for seat in seats:
        seat_id = seat["id"]
        pos = seat.get("position", {})
        sx, sy = pos.get("x", 0), pos.get("y", 0)
        status = seat.get("status", "Empty")
        print(f"Seat {seat_id} at ({sx}, {sy}) status={status}")

        overlapping = False
        for i, det in enumerate(detections):
            if len(det) < 4:
                continue
            x1, y1, x2, y2 = int(det[0]), int(det[1]), int(det[2]), int(det[3])
            dist = _distance_box_to_point(x1, y1, x2, y2, sx, sy)
            overlaps = _box_overlaps_circle(x1, y1, x2, y2, sx, sy, radius)
            overlap_str = "OVERLAP" if overlaps else "NO OVERLAP"
            margin = radius - dist
            margin_str = f"+{margin:.1f}px inside" if margin > 0 else f"{abs(margin):.1f}px outside"
            print(f"  Detection {i+1}: {overlap_str}  distance={dist:.1f}px  margin={margin_str}")
            if overlaps:
                overlapping = True

        if not overlapping and detections:
            min_dist = min(
                _distance_box_to_point(int(d[0]), int(d[1]), int(d[2]), int(d[3]), sx, sy)
                for d in detections if len(d) >= 4
            )
            needed_radius = int(min_dist) + 5
            print(f"  -> Need radius >= {needed_radius}px to overlap, or move seat closer to detection.")
        print()

    print("=" * 60)
    print("To fix: increase seat_detection_radius_pixels in data/config.json,")
    print("or run python backend/calibrate_seats.py to reposition seats.")
    print("=" * 60 + "\n")


def create_diagram(debug_json_path: str, output_path: str) -> None:
    """Create a simple 640x480 diagram of boxes and seat circles (optional)."""
    try:
        import numpy as np
        import cv2
    except ImportError:
        print("Optional: install numpy and opencv-python to generate overlap_diagram.png")
        return

    path = Path(debug_json_path)
    if not path.exists():
        return

    with open(path, "r") as f:
        data = json.load(f)

    seats = data.get("seats", [])
    detections = data.get("last_person_detections") or []
    config = data.get("config", {})
    radius = config.get("seat_detection_radius_pixels", 65)

    img = np.ones((480, 640, 3), dtype=np.uint8) * 255

    for det in detections:
        if len(det) < 4:
            continue
        x1, y1, x2, y2 = int(det[0]), int(det[1]), int(det[2]), int(det[3])
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 100, 0), 2)
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.circle(img, (cx, cy), 5, (255, 100, 0), -1)

    for seat in seats:
        pos = seat.get("position", {})
        x, y = pos.get("x", 0), pos.get("y", 0)
        seat_id = seat["id"]
        overlaps = any(
            len(d) >= 4
            and _box_overlaps_circle(int(d[0]), int(d[1]), int(d[2]), int(d[3]), x, y, radius)
            for d in detections
        )
        color = (0, 200, 0) if overlaps else (0, 0, 255)
        cv2.circle(img, (x, y), radius, color, 2)
        cv2.putText(img, seat_id, (x - 20, y - radius - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.putText(img, f"Radius: {radius}px", (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.imwrite(output_path, img)
    print(f"Diagram saved to {output_path}")


def main() -> None:
    base = Path(__file__).parent.parent
    debug_file = base / "debug_status.json"
    if not debug_file.exists():
        debug_file = Path(__file__).parent / "debug_status.json"
    if not debug_file.exists():
        debug_file = Path("debug_status.json")

    if debug_file.exists():
        analyze_overlap(str(debug_file))
        create_diagram(str(debug_file), str(base / "overlap_diagram.png"))
    else:
        print("debug_status.json not found.")
        print("1. Open http://localhost:8000/api/debug-detection-status")
        print("2. Save the JSON as debug_status.json in the project root")
        print("3. Run this script again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
