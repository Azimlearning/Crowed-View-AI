"""
Vision engine for detecting seat occupancy using YOLOv8-Nano.
"""
import os
# PyTorch 2.6+ defaults to weights_only=True; YOLO checkpoints need weights_only=False (trusted Ultralytics source)
import torch
_torch_load = torch.load
def _torch_load_weights_only_false(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _torch_load(*args, **kwargs)
torch.load = _torch_load_weights_only_false

import json
import time
import threading
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
from ultralytics import YOLO

from models import Seat, Zone, EventConfig
from logger_config import get_logger

logger = get_logger(__name__)


class VisionEngine:
    """Handles YOLOv8 detection and seat status tracking."""
    
    def __init__(self, seating_map_path: str, config_path: str):
        """Initialize the vision engine with configuration."""
        self.seating_map_path = seating_map_path
        self.config_path = config_path
        self.model = None
        self.seats: Dict[str, Seat] = {}
        self.zones: Dict[str, Zone] = {}
        self.config: EventConfig = None
        self.lock = threading.Lock()
        self.running = False
        self.cap = None
        self._last_frame = None  # for debug snapshot (single frame, not history)
        self._is_video_file = False  # Track if using video file instead of camera
        self._last_person_detections = None  # Store last detections for visualization
        self._seat_scores: Dict[str, int] = {}  # Per-seat hysteresis score (-5 to +5) when use_hysteresis
        self._detection_roi = None  # (x_min, y_min, x_max, y_max) for ROI-based YOLO; None = full frame
        self._prev_gray = None  # Last frame grayscale (blurred) for motion check
        self._last_forced_detection_time = 0.0  # When we last ran YOLO (for 30s forced interval)

        self._load_config()
        self._load_seating_map()
        self._compute_detection_roi()
        self._load_yolo_model()
    
    def _load_config(self):
        """Load event configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            config_data = json.load(f)
        self.config = EventConfig(**config_data)
    
    def _validate_configuration(self):
        """Validate configuration and seating map for consistency and correctness."""
        errors = []
        warnings = []
        
        # Validate config values
        if self.config.detection_interval_seconds <= 0:
            errors.append("detection_interval_seconds must be positive")
        if self.config.stability_required_scans <= 0:
            errors.append("stability_required_scans must be positive")
        if self.config.seat_detection_radius_pixels <= 0:
            errors.append("seat_detection_radius_pixels must be positive")
        if not (0.0 <= self.config.person_detection_confidence_threshold <= 1.0):
            errors.append("person_detection_confidence_threshold must be between 0.0 and 1.0")
        
        # Camera bounds (640x480)
        CAMERA_WIDTH = 640
        CAMERA_HEIGHT = 480
        
        # Check seat coordinates and detect overlaps
        radius = self.config.seat_detection_radius_pixels
        seat_positions = []
        
        for zone_name, zone in self.zones.items():
            # Validate zone threshold
            if zone.empty_threshold_minutes <= 0:
                errors.append(f"Zone '{zone_name}' empty_threshold_minutes must be positive")
            
            for seat in zone.seats:
                # Validate coordinates
                if seat.x < 0 or seat.x >= CAMERA_WIDTH:
                    errors.append(f"Seat '{seat.id}' x coordinate {seat.x} is out of bounds (0-{CAMERA_WIDTH-1})")
                if seat.y < 0 or seat.y >= CAMERA_HEIGHT:
                    errors.append(f"Seat '{seat.id}' y coordinate {seat.y} is out of bounds (0-{CAMERA_HEIGHT-1})")
                
                # Check for overlapping detection radii (warn only; allow larger radius for better detection)
                for other_seat_pos in seat_positions:
                    other_id, other_x, other_y = other_seat_pos
                    distance = sqrt((seat.x - other_x) ** 2 + (seat.y - other_y) ** 2)
                    min_distance = 2 * radius + 20  # Recommended spacing
                    if distance < 2 * radius:
                        warnings.append(f"Seat '{seat.id}' detection radius overlaps with seat '{other_id}' (distance: {distance:.1f}px)")
                    elif distance < min_distance:
                        warnings.append(f"Seat '{seat.id}' is close to '{other_id}' (distance: {distance:.1f}px, recommended: {min_distance}px)")
                
                seat_positions.append((seat.id, seat.x, seat.y))
        
        # Check for zones in config.json that don't have seats
        config_zone_names = {zc.name for zc in self.config.zones}
        seating_zone_names = set(self.zones.keys())
        missing_zones = config_zone_names - seating_zone_names
        if missing_zones:
            warnings.append(f"Zones in config.json have no seats: {', '.join(missing_zones)}")
        
        # Log errors and warnings
        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            warning_msg = "Configuration warnings:\n" + "\n".join(f"  - {w}" for w in warnings)
            logger.warning(warning_msg)
    
    def _load_seating_map(self):
        """Load seating map and initialize seat objects."""
        with open(self.seating_map_path, 'r') as f:
            seating_data = json.load(f)
        
        # Create zone config lookup
        zone_configs = {zc.name: zc for zc in self.config.zones}
        
        for zone_data in seating_data['zones']:
            zone_name = zone_data['name']
            zone_config = zone_configs.get(zone_name)
            
            if not zone_config:
                logger.warning(f"Zone '{zone_name}' not found in config.json")
                continue
            
            seats_list = []
            for seat_data in zone_data['seats']:
                seat = Seat(
                    id=seat_data['id'],
                    x=seat_data['x'],
                    y=seat_data['y'],
                    zone=zone_name,
                    status="Empty",
                    stability_counter=0,
                    last_empty_time=None,  # Only set when transitioning from Occupied to Empty
                    is_actionable=False
                )
                self.seats[seat.id] = seat
                seats_list.append(seat)
            
            zone = Zone(
                name=zone_name,
                seats=seats_list,
                empty_threshold_minutes=zone_config.empty_threshold_minutes
            )
            self.zones[zone_name] = zone

        # Initialize hysteresis scores when hysteresis is used (keep existing scores if reloading)
        self._seat_scores = {sid: self._seat_scores.get(sid, 0) for sid in self.seats}
        
        # Validate configuration after loading
        self._validate_configuration()

    def _compute_detection_roi(self) -> None:
        """Compute ROI bounding box from seat positions (radius + 50 margin), clamped to 640x480."""
        if not self.seats:
            self._detection_roi = None
            return
        radius = self.config.seat_detection_radius_pixels
        margin = radius + 50
        x_min = min(s.x for s in self.seats.values()) - margin
        y_min = min(s.y for s in self.seats.values()) - margin
        x_max = max(s.x for s in self.seats.values()) + margin
        y_max = max(s.y for s in self.seats.values()) + margin
        x_min = max(0, min(x_min, 639))
        y_min = max(0, min(y_min, 479))
        x_max = max(0, min(x_max, 640))
        y_max = max(0, min(y_max, 480))
        if x_max <= x_min or y_max <= y_min:
            self._detection_roi = None
            return
        self._detection_roi = (x_min, y_min, x_max, y_max)

    def _load_yolo_model(self):
        """Initialize YOLOv8-Nano model."""
        logger.info("Loading YOLOv8-Nano model...")
        self.model = YOLO('yolov8n.pt')  # Nano model for CPU inference
        logger.info("YOLOv8-Nano model loaded successfully")
    
    def _is_frame_valid(self, frame) -> bool:
        """
        Check if frame is valid (not all black/closed camera).
        
        Returns:
            True if frame has sufficient brightness, False if too dark
        """
        if frame is None or frame.size == 0:
            return False
        # Convert to grayscale and calculate mean brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = gray.mean()
        # Threshold: if mean brightness < 15, consider frame invalid (too dark)
        return mean_brightness >= 15

    def _has_motion(self, frame, pixel_threshold: int = 500) -> bool:
        """
        Compare current frame to previous grayscale blurred frame; if diff has few non-zero pixels, no motion.
        Updates self._prev_gray for next call.
        """
        if frame is None or frame.size == 0:
            return True
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        if self._prev_gray is None:
            self._prev_gray = blurred.copy()
            return True
        diff = cv2.absdiff(self._prev_gray, blurred)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        self._prev_gray = blurred.copy()
        return cv2.countNonZero(thresh) >= pixel_threshold

    @staticmethod
    def _box_overlaps_circle(x1: int, y1: int, x2: int, y2: int, cx: int, cy: int, radius: int) -> bool:
        """Check if bounding box (x1,y1,x2,y2) overlaps circle centered at (cx,cy) with given radius."""
        nearest_x = max(x1, min(cx, x2))
        nearest_y = max(y1, min(cy, y2))
        distance = sqrt((nearest_x - cx) ** 2 + (nearest_y - cy) ** 2)
        return distance <= radius

    @staticmethod
    def _distance_box_to_point(x1: int, y1: int, x2: int, y2: int, px: int, py: int) -> float:
        """Distance from circle center to nearest point on bounding box (for closest-seat tiebreak)."""
        nearest_x = max(x1, min(px, x2))
        nearest_y = max(y1, min(py, y2))
        return sqrt((nearest_x - px) ** 2 + (nearest_y - py) ** 2)

    def detect_persons(self, frame) -> List[Tuple[int, int, int, int]]:
        """
        Detect persons in the frame using YOLOv8.
        If _detection_roi is set, runs YOLO on that crop and maps boxes back to full-frame coordinates.
        
        Returns:
            List of bounding boxes as (x1, y1, x2, y2) tuples
        """
        roi = self._detection_roi
        if roi is not None:
            x_min, y_min, x_max, y_max = roi
            roi_frame = frame[y_min:y_max, x_min:x_max]
            if roi_frame.size == 0:
                return []
            results = self.model(roi_frame, verbose=False)
            offset_x, offset_y = x_min, y_min
        else:
            results = self.model(frame, verbose=False)
            offset_x, offset_y = 0, 0

        person_detections = []
        threshold = getattr(self.config, 'person_detection_confidence_threshold', 0.3)
        debug = getattr(self.config, 'debug_detection', False)

        for result in results:
            boxes = result.boxes
            for box in boxes:
                if int(box.cls) == 0:
                    conf = float(box.conf[0]) if hasattr(box.conf, '__len__') else float(box.conf)
                    if conf >= threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = int(x1) + offset_x, int(y1) + offset_y, int(x2) + offset_x, int(y2) + offset_y
                        person_detections.append((x1, y1, x2, y2))
                        if debug:
                            logger.debug(f"Person detected: confidence={conf:.2f}, bbox=({x1},{y1},{x2},{y2})")
                    elif debug:
                        logger.debug(f"Person detection below threshold: confidence={conf:.2f} < {threshold}")

        return person_detections
    
    def check_seat_occupancy(self, person_detections: List[Tuple[int, int, int, int]], 
                            seat: Seat) -> bool:
        """
        Check if a seat is occupied based on person detections (bounding box overlap with seat circle).
        """
        radius = self.config.seat_detection_radius_pixels
        for x1, y1, x2, y2 in person_detections:
            if self._box_overlaps_circle(x1, y1, x2, y2, seat.x, seat.y, radius):
                return True
        return False
    
    def _update_seat_with_hysteresis(self, seat: Seat, is_occupied: bool):
        """
        Update seat using a per-seat score; switch Empty<->Occupied only at config thresholds.
        Reduces flicker when a person is on the seat boundary.
        """
        score = self._seat_scores.get(seat.id, 0)
        if is_occupied:
            score = min(5, score + 1)
        else:
            score = max(-5, score - 1)
        self._seat_scores[seat.id] = score

        occ_th = getattr(self.config, "hysteresis_occupied_threshold", 3)
        empty_th = getattr(self.config, "hysteresis_empty_threshold", -3)

        if seat.status == "Empty" and score >= occ_th:
            seat.status = "Occupied"
            seat.last_empty_time = None
            seat.is_actionable = False
        elif seat.status == "Occupied" and score <= empty_th:
            seat.status = "Empty"
            seat.last_empty_time = datetime.now()
            seat.is_actionable = False

    def update_seat_status(self, seat: Seat, is_occupied: bool):
        """
        Update seat status with stability counter logic.
        
        Args:
            seat: Seat object to update
            is_occupied: Current detection result
        """
        if getattr(self.config, "use_hysteresis", False):
            self._update_seat_with_hysteresis(seat, is_occupied)
            return

        current_status = "Occupied" if is_occupied else "Empty"
        expected_status = seat.status
        
        if current_status == expected_status:
            # Detection matches current status, increment counter
            seat.stability_counter += 1
        else:
            # Detection differs, start counting from 1 for the new state
            seat.stability_counter = 1
        
        # Only update status if stability threshold is reached
        if seat.stability_counter >= self.config.stability_required_scans:
            if seat.status != current_status:
                seat.status = current_status
                
                # Update time tracking
                if current_status == "Empty":
                    seat.last_empty_time = datetime.now()
                    seat.is_actionable = False
                else:
                    seat.last_empty_time = None
                    seat.is_actionable = False
    
    def update_actionable_flags(self):
        """Update actionable flags based on empty duration thresholds."""
        current_time = datetime.now()
        
        for zone_name, zone in self.zones.items():
            threshold_minutes = zone.empty_threshold_minutes
            
            for seat in zone.seats:
                # Only mark as actionable if seat was previously occupied and is now empty
                # Seats that have been empty since initialization should not be actionable
                if seat.status == "Empty" and seat.last_empty_time is not None:
                    empty_duration = (current_time - seat.last_empty_time).total_seconds() / 60
                    seat.is_actionable = empty_duration >= threshold_minutes
                else:
                    # Reset actionable flag if seat is occupied or never was occupied
                    seat.is_actionable = False
    
    def get_all_seats(self) -> Dict[str, Seat]:
        """Get a copy of all seat states (thread-safe)."""
        with self.lock:
            return {seat_id: Seat(**seat.model_dump()) for seat_id, seat in self.seats.items()}
    
    def get_zones(self) -> Dict[str, Zone]:
        """Get a copy of all zones (thread-safe)."""
        with self.lock:
            return {zone_name: Zone(**zone.model_dump()) for zone_name, zone in self.zones.items()}
    
    def _open_webcam(self):
        """Try to open webcam or video file; on Windows use DirectShow first, then try indices 0, 1, 2."""
        import sys
        
        # Check for video file path in environment variable
        video_path = os.getenv("VIDEO_FILE_PATH")
        if video_path and Path(video_path).exists():
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                self.cap = cap
                self._is_video_file = True
                logger.info(f"Video file opened: {video_path}")
                return True
            else:
                logger.warning(f"Could not open video file: {video_path}, falling back to camera")
        
        # Try to open webcam
        self._is_video_file = False
        try:
            env_idx = os.getenv("CAMERA_INDEX")
            if env_idx is not None:
                indices = [int(env_idx)]
                logger.info(f"Using camera index from CAMERA_INDEX: {env_idx}")
            else:
                indices = [0, 1, 2]
        except ValueError:
            indices = [0, 1, 2]
        
        if sys.platform == "win32":
            # On Windows, DirectShow (CAP_DSHOW) often works better than default MSMF
            for idx in indices:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    self.cap = cap
                    logger.info(f"Webcam opened: index {idx} (DirectShow)")
                    return True
            logger.warning("DirectShow failed for indices 0,1,2; trying default backend...")
        
        for idx in indices:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                self.cap = cap
                logger.info(f"Webcam opened: index {idx}")
                return True
        
        return False

    def main_detection_loop(self):
        """Main detection loop running in a separate thread."""
        logger.info("Starting vision engine detection loop...")
        if not self._open_webcam():
            logger.error("Could not open webcam. Try closing other apps using the camera, or set CAMERA_INDEX=1 (or 2) in .env")
            return
        
        # Set camera resolution (optional, adjust as needed)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.running = True
        last_detection_time = 0
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    if self._is_video_file:
                        # Video file ended, restart from beginning
                        logger.info("Video file ended, restarting from beginning")
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.cap.read()
                        if not ret:
                            logger.error("Failed to restart video file")
                            break
                    else:
                        logger.warning("Failed to read frame from webcam")
                        time.sleep(1)
                        continue
                
                current_time = time.time()
                elapsed = current_time - last_detection_time
                
                # Only run detection at specified interval
                if elapsed >= self.config.detection_interval_seconds:
                    # Make a copy of frame for detection (outside lock for performance)
                    detection_frame = frame.copy()
                    
                    with self.lock:
                        # Update latest frame for live stream (smooth feed)
                        self._last_frame = frame.copy()
                        
                        # Check if frame is valid (not black/closed camera)
                        if not self._is_frame_valid(detection_frame):
                            # Frame is too dark/invalid - mark all seats as Empty
                            # Only update last_empty_time if seat was previously occupied
                            for seat in self.seats.values():
                                was_occupied = seat.status == "Occupied"
                                seat.status = "Empty"
                                seat.stability_counter = self.config.stability_required_scans
                                if was_occupied:
                                    seat.last_empty_time = datetime.now()
                                # Don't set last_empty_time if seat was already empty
                                seat.is_actionable = False
                            logger.warning("Frame invalid (too dark) - all seats marked Empty")
                        else:
                            # Motion-based skip: when scene is static, skip YOLO; run at least every 30s
                            has_motion = self._has_motion(detection_frame)
                            force_interval = 30
                            time_since_forced = current_time - self._last_forced_detection_time
                            skip_yolo = (not has_motion) and (time_since_forced < force_interval)
                            if skip_yolo:
                                logger.debug("No motion; skipping YOLO (keeping previous seat state)")
                            else:
                                person_detections = self.detect_persons(detection_frame)
                                # Store detections for overlay drawing
                                self._last_person_detections = person_detections
                                radius = self.config.seat_detection_radius_pixels
                                debug = getattr(self.config, 'debug_detection', False)
                                if debug:
                                    logger.debug(f"Detected {len(person_detections)} persons")
                                
                                # One-to-one assignment: each detection -> at most one seat (closest);
                                # each seat -> at most one detection. Prevents one person marking multiple seats.
                                seat_occupancy = {seat.id: False for seat in self.seats.values()}
                                matches = []
                                for det_idx, (x1, y1, x2, y2) in enumerate(person_detections):
                                    for seat in self.seats.values():
                                        if self._box_overlaps_circle(x1, y1, x2, y2, seat.x, seat.y, radius):
                                            dist = self._distance_box_to_point(x1, y1, x2, y2, seat.x, seat.y)
                                            matches.append((dist, det_idx, seat.id))
                                matches.sort(key=lambda x: x[0])
                                used_detections = set()
                                assigned_seats = set()
                                for dist, det_idx, seat_id in matches:
                                    if det_idx in used_detections or seat_id in assigned_seats:
                                        continue
                                    seat_occupancy[seat_id] = True
                                    used_detections.add(det_idx)
                                    assigned_seats.add(seat_id)
                                    if debug:
                                        logger.debug(f"Assigned detection {det_idx} to seat {seat_id} (distance: {dist:.1f}px)")
                                
                                # Update seat statuses based on assignment
                                for seat in self.seats.values():
                                    is_occupied = seat_occupancy.get(seat.id, False)
                                    self.update_seat_status(seat, is_occupied)
                                
                                if debug:
                                    occupied_ids = [sid for sid, occ in seat_occupancy.items() if occ]
                                    logger.debug(f"Seats marked occupied: {occupied_ids}")
                                    logger.debug(f"Total person detections: {len(person_detections)}")
                                    if person_detections:
                                        logger.debug(f"Person bounding boxes: {person_detections}")
                                    for seat in self.seats.values():
                                        logger.debug(f"Seat {seat.id}: status={seat.status}, stability={seat.stability_counter}, occupied={seat_occupancy.get(seat.id, False)}")
                                
                                # Update actionable flags
                                self.update_actionable_flags()
                                self._last_forced_detection_time = current_time
                    
                    last_detection_time = current_time
                    logger.debug(f"Detection completed at {datetime.now().strftime('%H:%M:%S')}")
                else:
                    # Update frame even when not detecting (for smooth stream)
                    with self.lock:
                        self._last_frame = frame.copy()
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Detection loop interrupted")
        finally:
            self.cleanup()
    
    def _draw_seat_overlay(self, img, person_detections: List[Tuple[int, int, int, int]] = None):
        """Draw seat circles and labels on image (mutates img)."""
        radius = self.config.seat_detection_radius_pixels
        debug = getattr(self.config, 'debug_detection', False)
        
        # Draw person detections if debug mode enabled
        if debug and person_detections:
            for x1, y1, x2, y2 in person_detections:
                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 2)  # Cyan boxes
                # Draw center point
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.circle(img, (cx, cy), 5, (255, 255, 0), -1)
        
        # Draw seats
        for seat in self.seats.values():
            x, y = seat.x, seat.y
            # Green = Empty, Red = Occupied (seat taken)
            color = (0, 255, 0) if seat.status == "Empty" else (0, 0, 255)
            if seat.is_actionable:
                color = (0, 165, 255)  # orange
            cv2.circle(img, (x, y), radius, color, 2)
            cv2.putText(img, seat.id, (x - 20, y - radius - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def get_debug_frame_png(self) -> bytes | None:
        """Return a PNG image of the last camera frame with seat circles and labels drawn (for testing)."""
        with self.lock:
            if self._last_frame is None:
                return None
            img = self._last_frame.copy()
            # Get last person detections if available (stored during detection)
            person_detections = getattr(self, '_last_person_detections', None)
        self._draw_seat_overlay(img, person_detections)
        _, buf = cv2.imencode(".png", img)
        return buf.tobytes()

    def get_latest_frame_jpeg(self) -> bytes | None:
        """Return the latest camera frame with seat overlay as JPEG (for live stream)."""
        try:
            with self.lock:
                if self._last_frame is None:
                    return None
                img = self._last_frame.copy()
                # Get last person detections if available
                person_detections = getattr(self, '_last_person_detections', None)
            
            self._draw_seat_overlay(img, person_detections)
            success, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success or buf is None:
                return None
            return buf.tobytes()
        except Exception as e:
            logger.error(f"Error encoding frame to JPEG: {e}", exc_info=True)
            return None

    def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        logger.info("Vision engine cleaned up")


def start_vision_engine(seating_map_path: str, config_path: str) -> VisionEngine:
    """Start the vision engine in a background thread."""
    engine = VisionEngine(seating_map_path, config_path)
    thread = threading.Thread(target=engine.main_detection_loop, daemon=True)
    thread.start()
    return engine
