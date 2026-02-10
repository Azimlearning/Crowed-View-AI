"""
Interactive seat calibration tool for Venue Intelligence AI.
Click to place seats, drag to adjust, right-click to delete.
"""
import sys
import json
import cv2
from pathlib import Path
from typing import List, Tuple, Optional

# Camera resolution
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Default detection radius (will be read from config)
DEFAULT_RADIUS = 65


class SeatCalibrator:
    """Interactive seat calibration tool."""
    
    def __init__(self, seating_map_path: str, config_path: str):
        self.seating_map_path = Path(seating_map_path)
        self.config_path = Path(config_path)
        self.seats: List[dict] = []
        self.dragging_seat: Optional[int] = None
        self.current_zone = "VIP"
        self.radius = DEFAULT_RADIUS
        
        # Load existing seats if file exists
        self._load_existing_seats()
        self._load_config()
        
        # Camera
        self.cap = None
        self._open_camera()
        
        # Window setup
        self.window_name = "Seat Calibration Tool"
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)
        
    def _load_config(self):
        """Load detection radius from config."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.radius = config.get('seat_detection_radius_pixels', DEFAULT_RADIUS)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    
    def _load_existing_seats(self):
        """Load existing seats from JSON file."""
        if self.seating_map_path.exists():
            try:
                with open(self.seating_map_path, 'r') as f:
                    data = json.load(f)
                    # Flatten all seats from all zones
                    for zone in data.get('zones', []):
                        for seat in zone.get('seats', []):
                            seat['zone'] = zone['name']
                            self.seats.append(seat)
            except Exception as e:
                print(f"Warning: Could not load existing seats: {e}")
    
    def _open_camera(self):
        """Open camera."""
        import os
        import sys
        
        # Try camera indices
        indices = [0, 1, 2]
        if sys.platform == "win32":
            # Try DirectShow first on Windows
            for idx in indices:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                    self.cap = cap
                    print(f"Camera opened: index {idx}")
                    return
        
        # Fallback to default backend
        for idx in indices:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                self.cap = cap
                print(f"Camera opened: index {idx}")
                return
        
        print("Error: Could not open camera")
        sys.exit(1)
    
    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events."""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check if clicking on existing seat
            clicked_seat_idx = self._get_seat_at_position(x, y)
            if clicked_seat_idx is not None:
                self.dragging_seat = clicked_seat_idx
            else:
                # Add new seat
                seat_id = f"{self.current_zone.lower()}_{len([s for s in self.seats if s.get('zone') == self.current_zone]) + 1}"
                self.seats.append({
                    'id': seat_id,
                    'x': x,
                    'y': y,
                    'zone': self.current_zone
                })
        
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.dragging_seat is not None:
                # Update seat position
                self.seats[self.dragging_seat]['x'] = max(0, min(CAMERA_WIDTH - 1, x))
                self.seats[self.dragging_seat]['y'] = max(0, min(CAMERA_HEIGHT - 1, y))
        
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging_seat = None
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Delete seat
            clicked_seat_idx = self._get_seat_at_position(x, y)
            if clicked_seat_idx is not None:
                self.seats.pop(clicked_seat_idx)
    
    def _get_seat_at_position(self, x: int, y: int) -> Optional[int]:
        """Get seat index at given position."""
        for i, seat in enumerate(self.seats):
            sx, sy = seat['x'], seat['y']
            distance = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
            if distance < self.radius:
                return i
        return None
    
    def _draw_overlay(self, frame):
        """Draw seat markers and instructions on frame."""
        # Draw seats
        for seat in self.seats:
            x, y = seat['x'], seat['y']
            zone = seat.get('zone', 'Unknown')
            
            # Color by zone
            if zone == 'VIP':
                color = (0, 255, 255)  # Yellow
            else:
                color = (255, 0, 255)  # Magenta
            
            # Draw circle
            cv2.circle(frame, (x, y), self.radius, color, 2)
            cv2.circle(frame, (x, y), 3, color, -1)
            
            # Draw seat ID
            cv2.putText(frame, seat['id'], (x - 20, y - self.radius - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw instructions
        instructions = [
            "LEFT CLICK: Add seat",
            "DRAG: Move seat",
            "RIGHT CLICK: Delete seat",
            f"ZONE: {self.current_zone} (Press 1-9 to change)",
            "S: Save and exit",
            "Q: Quit without saving",
            "C: Clear all seats"
        ]
        
        y_offset = 20
        for i, text in enumerate(instructions):
            cv2.putText(frame, text, (10, y_offset + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw zone summary
        zones = {}
        for seat in self.seats:
            zone = seat.get('zone', 'Unknown')
            zones[zone] = zones.get(zone, 0) + 1
        
        summary_y = CAMERA_HEIGHT - 60
        cv2.putText(frame, "Zone Summary:", (10, summary_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        for i, (zone, count) in enumerate(zones.items()):
            cv2.putText(frame, f"  {zone}: {count} seats", (10, summary_y + 20 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _save_seats(self):
        """Save seats to JSON file grouped by zone."""
        # Group seats by zone
        zones_dict = {}
        for seat in self.seats:
            zone_name = seat.get('zone', 'Standard')
            if zone_name not in zones_dict:
                zones_dict[zone_name] = []
            
            # Create seat entry (without zone, as it's in the zone dict)
            seat_entry = {
                'id': seat['id'],
                'x': seat['x'],
                'y': seat['y']
            }
            zones_dict[zone_name].append(seat_entry)
        
        # Create output structure
        output = {
            'zones': [
                {
                    'name': zone_name,
                    'seats': seats
                }
                for zone_name, seats in zones_dict.items()
            ]
        }
        
        # Save to file
        with open(self.seating_map_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nSaved {len(self.seats)} seats to {self.seating_map_path}")
        print(f"Zones: {', '.join(zones_dict.keys())}")
    
    def run(self):
        """Run calibration tool."""
        print("\n" + "=" * 60)
        print("Seat Calibration Tool")
        print("=" * 60)
        print("\nControls:")
        print("  LEFT CLICK: Add seat at cursor position")
        print("  DRAG: Move existing seat")
        print("  RIGHT CLICK: Delete seat")
        print("  1-9: Change zone (1=VIP, 2=Standard, etc.)")
        print("  S: Save and exit")
        print("  Q: Quit without saving")
        print("  C: Clear all seats")
        print("\nPress any key in the window to start...")
        
        zone_map = {
            ord('1'): 'VIP',
            ord('2'): 'Standard',
            ord('3'): 'Premium',
            ord('4'): 'Economy',
            ord('5'): 'Zone5',
            ord('6'): 'Zone6',
            ord('7'): 'Zone7',
            ord('8'): 'Zone8',
            ord('9'): 'Zone9',
        }
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to read frame")
                break
            
            # Draw overlay
            self._draw_overlay(frame)
            
            cv2.imshow(self.window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nExiting without saving...")
                break
            elif key == ord('s'):
                self._save_seats()
                break
            elif key == ord('c'):
                if len(self.seats) > 0:
                    confirm = input(f"\nClear all {len(self.seats)} seats? (y/n): ")
                    if confirm.lower() == 'y':
                        self.seats = []
                        print("All seats cleared")
            elif key in zone_map:
                self.current_zone = zone_map[key]
                print(f"Zone changed to: {self.current_zone}")
        
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    """Main entry point."""
    BASE_DIR = Path(__file__).parent.parent
    SEATING_MAP_PATH = BASE_DIR / "data" / "seating_map.json"
    CONFIG_PATH = BASE_DIR / "data" / "config.json"
    
    # Create data directory if it doesn't exist
    SEATING_MAP_PATH.parent.mkdir(exist_ok=True)
    
    calibrator = SeatCalibrator(str(SEATING_MAP_PATH), str(CONFIG_PATH))
    calibrator.run()


if __name__ == "__main__":
    main()
