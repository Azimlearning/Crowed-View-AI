"""
Vision engine for detecting seat occupancy using YOLOv8-Nano.

Uses area-based overlap (60% rule) with temporal confirmation:
- Occupancy: 60% overlap sustained for 30 seconds → Occupied
- Vacancy: 20-minute grace period after person leaves → Empty
- Testing mode: bypasses all timers for instant updates
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
from typing import Dict, List, Tuple, Optional

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
        self._detection_roi = None  # (x_min, y_min, x_max, y_max) for ROI-based YOLO; None = full frame
        self._prev_gray = None  # Last frame grayscale (blurred) for motion check
        self._last_forced_detection_time = 0.0  # When we last ran YOLO (for 30s forced interval)

        # Temporal tracking for new occupancy logic
        self._seat_first_overlap_time: Dict[str, Optional[datetime]] = {}  # When 60% overlap first started
        self._seat_last_overlap: Dict[str, float] = {}  # Last computed overlap per seat

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
        if not (0.0 < self.config.occupancy_overlap_threshold <= 1.0):
            errors.append("occupancy_overlap_threshold must be between 0.0 and 1.0")
        if self.config.occupancy_confirmation_seconds < 0:
            errors.append("occupancy_confirmation_seconds must be non-negative")
        if self.config.vacancy_grace_period_minutes < 0:
            errors.append("vacancy_grace_period_minutes must be non-negative")
        if not (0.0 <= self.config.person_detection_confidence_threshold <= 1.0):
            errors.append("person_detection_confidence_threshold must be between 0.0 and 1.0")
        
        # Camera bounds (640x480)
        CAMERA_WIDTH = 640
        CAMERA_HEIGHT = 480
        
        for zone_name, zone in self.zones.items():
            # Validate zone threshold
            if zone.empty_threshold_minutes <= 0:
                errors.append(f"Zone '{zone_name}' empty_threshold_minutes must be positive")
            
            for seat in zone.seats:
                # Validate seat rectangle stays within camera bounds
                if seat.x < 0 or seat.x >= CAMERA_WIDTH:
                    warnings.append(f"Seat '{seat.id}' x coordinate {seat.x} is out of bounds (0-{CAMERA_WIDTH-1})")
                if seat.y < 0 or seat.y >= CAMERA_HEIGHT:
                    warnings.append(f"Seat '{seat.id}' y coordinate {seat.y} is out of bounds (0-{CAMERA_HEIGHT-1})")
                if seat.x + seat.width > CAMERA_WIDTH:
                    warnings.append(f"Seat '{seat.id}' extends beyond camera width (x={seat.x}, w={seat.width})")
                if seat.y + seat.height > CAMERA_HEIGHT:
                    warnings.append(f"Seat '{seat.id}' extends beyond camera height (y={seat.y}, h={seat.height})")
                if seat.width <= 0 or seat.height <= 0:
                    errors.append(f"Seat '{seat.id}' width/height must be positive")
        
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
                    width=seat_data.get('width', 100),
                    height=seat_data.get('height', 100),
                    zone=zone_name,
                    status="Empty",
                    stability_counter=0,
                    last_empty_time=None,
                    is_actionable=False,
                    overlap_percentage=0.0,
                    vacancy_timer_start=None
                )
                self.seats[seat.id] = seat
                seats_list.append(seat)
            
            zone = Zone(
                name=zone_name,
                seats=seats_list,
                empty_threshold_minutes=zone_config.empty_threshold_minutes
            )
            self.zones[zone_name] = zone

        # Initialize temporal tracking
        for sid in self.seats:
            if sid not in self._seat_first_overlap_time:
                self._seat_first_overlap_time[sid] = None
            if sid not in self._seat_last_overlap:
                self._seat_last_overlap[sid] = 0.0
        
        # Validate configuration after loading
        self._validate_configuration()

    def _compute_detection_roi(self) -> None:
        """Compute ROI bounding box from seat positions (margin around seat rects), clamped to 640x480."""
        if not self.seats:
            self._detection_roi = None
            return
        margin = 50
        x_min = min(s.x for s in self.seats.values()) - margin
        y_min = min(s.y for s in self.seats.values()) - margin
        x_max = max(s.x + s.width for s in self.seats.values()) + margin
        y_max = max(s.y + s.height for s in self.seats.values()) + margin
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

    # -----------------------------------------------------------------------
    # Area-based overlap computation
    # -----------------------------------------------------------------------

    @staticmethod
    def _compute_rect_intersection_area(
        ax1: int, ay1: int, ax2: int, ay2: int,
        bx1: int, by1: int, bx2: int, by2: int
    ) -> int:
        """Compute the intersection area of two axis-aligned rectangles.
        
        Each rectangle is defined by (x1, y1, x2, y2) where (x1,y1) is the
        top-left corner and (x2,y2) is the bottom-right corner.
        
        Returns:
            Intersection area in pixels squared, or 0 if no overlap.
        """
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0
        return (ix2 - ix1) * (iy2 - iy1)

    def compute_seat_overlap(
        self,
        seat: Seat,
        person_detections: List[Tuple[int, int, int, int]]
    ) -> float:
        """Compute cumulative overlap percentage for a seat.
        
        Multiple person bounding boxes can contribute to the same seat.
        Their individual intersection areas are summed and divided by the seat area.
        The result is capped at 1.0.
        
        Args:
            seat: The Seat object (defines the static area A1).
            person_detections: List of (x1, y1, x2, y2) bounding boxes (dynamic area A2).
            
        Returns:
            Overlap fraction (0.0 to 1.0).
        """
        seat_x1 = seat.x
        seat_y1 = seat.y
        seat_x2 = seat.x + seat.width
        seat_y2 = seat.y + seat.height
        seat_area = seat.width * seat.height
        if seat_area <= 0:
            return 0.0

        total_intersection = 0
        for (px1, py1, px2, py2) in person_detections:
            total_intersection += self._compute_rect_intersection_area(
                seat_x1, seat_y1, seat_x2, seat_y2,
                px1, py1, px2, py2
            )

        return min(total_intersection / seat_area, 1.0)

    # -----------------------------------------------------------------------
    # Temporal occupancy logic
    # -----------------------------------------------------------------------

    def update_seat_status(self, seat: Seat, overlap: float):
        """Update seat status using area-overlap + temporal logic.
        
        Rules:
        - Occupancy Confirmation: overlap >= threshold must be sustained for
          `occupancy_confirmation_seconds` before flipping Empty → Occupied.
        - Vacancy Grace Period: when overlap drops below threshold, a timer starts.
          Seat stays Occupied for `vacancy_grace_period_minutes`. If overlap returns
          above threshold during grace, the timer is cancelled.
        - Testing Mode: all timers bypassed; status changes instantly.
        """
        threshold = self.config.occupancy_overlap_threshold
        now = datetime.now()
        testing = self.config.testing_mode

        # Store the current overlap on the seat for frontend display
        seat.overlap_percentage = overlap

        is_covered = overlap >= threshold

        if seat.status == "Empty":
            if is_covered:
                if testing:
                    # Instant flip in testing mode
                    seat.status = "Occupied"
                    seat.last_empty_time = None
                    seat.is_actionable = False
                    seat.vacancy_timer_start = None
                    self._seat_first_overlap_time[seat.id] = None
                else:
                    # Start or continue confirmation timer
                    if self._seat_first_overlap_time.get(seat.id) is None:
                        self._seat_first_overlap_time[seat.id] = now
                    
                    elapsed = (now - self._seat_first_overlap_time[seat.id]).total_seconds()
                    if elapsed >= self.config.occupancy_confirmation_seconds:
                        # Confirmed occupied
                        seat.status = "Occupied"
                        seat.last_empty_time = None
                        seat.is_actionable = False
                        seat.vacancy_timer_start = None
                        self._seat_first_overlap_time[seat.id] = None
            else:
                # Not covered — reset confirmation timer
                self._seat_first_overlap_time[seat.id] = None

        elif seat.status == "Occupied":
            if is_covered:
                # Still occupied — cancel any pending vacancy timer
                seat.vacancy_timer_start = None
                self._seat_first_overlap_time[seat.id] = None
            else:
                if testing:
                    # Instant flip in testing mode
                    seat.status = "Empty"
                    seat.last_empty_time = now
                    seat.is_actionable = False
                    seat.vacancy_timer_start = None
                    self._seat_first_overlap_time[seat.id] = None
                else:
                    # Start or continue vacancy grace period
                    if seat.vacancy_timer_start is None:
                        seat.vacancy_timer_start = now
                    
                    elapsed_minutes = (now - seat.vacancy_timer_start).total_seconds() / 60.0
                    if elapsed_minutes >= self.config.vacancy_grace_period_minutes:
                        # Grace period expired — mark as Empty
                        seat.status = "Empty"
                        seat.last_empty_time = now
                        seat.is_actionable = False
                        seat.vacancy_timer_start = None
                        self._seat_first_overlap_time[seat.id] = None

    def update_actionable_flags(self):
        """Update actionable flags based on empty duration thresholds."""
        current_time = datetime.now()
        
        for zone_name, zone in self.zones.items():
            threshold_minutes = zone.empty_threshold_minutes
            
            for seat in zone.seats:
                # Only mark as actionable if seat was previously occupied and is now empty
                if seat.status == "Empty" and seat.last_empty_time is not None:
                    empty_duration = (current_time - seat.last_empty_time).total_seconds() / 60
                    seat.is_actionable = empty_duration >= threshold_minutes
                else:
                    seat.is_actionable = False

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
    
    # -----------------------------------------------------------------------
    # Thread-safe accessors
    # -----------------------------------------------------------------------

    def get_all_seats(self) -> Dict[str, Seat]:
        """Get a copy of all seat states (thread-safe)."""
        with self.lock:
            return {seat_id: Seat(**seat.model_dump()) for seat_id, seat in self.seats.items()}
    
    def get_zones(self) -> Dict[str, Zone]:
        """Get a copy of all zones (thread-safe)."""
        with self.lock:
            return {zone_name: Zone(**zone.model_dump()) for zone_name, zone in self.zones.items()}

    # -----------------------------------------------------------------------
    # Camera management
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Main detection loop
    # -----------------------------------------------------------------------

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
                            for seat in self.seats.values():
                                was_occupied = seat.status == "Occupied"
                                seat.status = "Empty"
                                seat.overlap_percentage = 0.0
                                seat.vacancy_timer_start = None
                                self._seat_first_overlap_time[seat.id] = None
                                if was_occupied:
                                    seat.last_empty_time = datetime.now()
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
                                # Even when skipping, we still need to progress temporal timers
                                for seat in self.seats.values():
                                    last_overlap = self._seat_last_overlap.get(seat.id, 0.0)
                                    self.update_seat_status(seat, last_overlap)
                            else:
                                person_detections = self.detect_persons(detection_frame)
                                # Store detections for overlay drawing
                                self._last_person_detections = person_detections
                                debug = getattr(self.config, 'debug_detection', False)
                                if debug:
                                    logger.debug(f"Detected {len(person_detections)} persons")
                                
                                # Compute cumulative overlap for each seat and update status
                                for seat in self.seats.values():
                                    overlap = self.compute_seat_overlap(seat, person_detections)
                                    self._seat_last_overlap[seat.id] = overlap
                                    self.update_seat_status(seat, overlap)
                                    
                                    if debug:
                                        logger.debug(
                                            f"Seat {seat.id}: overlap={overlap:.2%}, "
                                            f"status={seat.status}, "
                                            f"vacancy_timer={'active' if seat.vacancy_timer_start else 'none'}"
                                        )
                                
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

    # -----------------------------------------------------------------------
    # Visualization
    # -----------------------------------------------------------------------

    def _draw_seat_overlay(self, img, person_detections: List[Tuple[int, int, int, int]] = None):
        """Draw seat rectangles and labels on image (mutates img)."""
        debug = getattr(self.config, 'debug_detection', False)
        
        # Draw person detections if debug mode enabled
        if debug and person_detections:
            for x1, y1, x2, y2 in person_detections:
                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 2)  # Cyan boxes
                # Draw center point
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                cv2.circle(img, (cx, cy), 5, (255, 255, 0), -1)
        
        # Draw seats as rectangles
        for seat in self.seats.values():
            sx1, sy1 = seat.x, seat.y
            sx2, sy2 = seat.x + seat.width, seat.y + seat.height
            
            # Color scheme: Red = Occupied, Grey = Unoccupied, Orange = Actionable
            if seat.is_actionable:
                color = (0, 165, 255)  # Orange (BGR)
            elif seat.status == "Occupied":
                color = (0, 0, 255)  # Red (BGR)
            else:
                color = (150, 150, 150)  # Grey (BGR)
            
            cv2.rectangle(img, (sx1, sy1), (sx2, sy2), color, 2)
            
            # Label: seat id + overlap %
            overlap_pct = int(seat.overlap_percentage * 100)
            label = f"{seat.id} ({overlap_pct}%)"
            cv2.putText(img, label, (sx1, sy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    def get_debug_frame_png(self) -> bytes | None:
        """Return a PNG image of the last camera frame with seat rectangles and labels drawn (for testing)."""
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

    # -----------------------------------------------------------------------
    # Runtime config update
    # -----------------------------------------------------------------------

    def update_config(self, **kwargs):
        """Update config parameters at runtime (thread-safe)."""
        with self.lock:
            for key, value in kwargs.items():
                if value is not None and hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.info(f"Config updated: {key} = {value}")


def start_vision_engine(seating_map_path: str, config_path: str) -> VisionEngine:
    """Start the vision engine in a background thread."""
    engine = VisionEngine(seating_map_path, config_path)
    thread = threading.Thread(target=engine.main_detection_loop, daemon=True)
    thread.start()
    return engine
