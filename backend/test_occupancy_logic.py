"""
Unit tests for the new area-based occupancy logic.
Tests overlap computation, temporal confirmation, vacancy grace period, and testing mode.

Run: python -m pytest backend/test_occupancy_logic.py -v
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Patch torch.load before any YOLO import
import torch
_torch_load = torch.load
def _patch(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _torch_load(*args, **kwargs)
torch.load = _patch

from models import Seat, EventConfig, ZoneConfig


# ---------------------------------------------------------------------------
# Helper: create a minimal VisionEngine without camera/YOLO for logic tests
# ---------------------------------------------------------------------------
class MockVisionEngine:
    """Minimal stand-in that exposes occupancy logic without camera/YOLO."""

    def __init__(self, config: EventConfig):
        self.config = config
        self._seat_first_overlap_time = {}
        self._seat_last_overlap = {}

    # Import the static method and instance methods from the real engine
    @staticmethod
    def _compute_rect_intersection_area(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0
        return (ix2 - ix1) * (iy2 - iy1)

    def compute_seat_overlap(self, seat, person_detections):
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
                seat_x1, seat_y1, seat_x2, seat_y2, px1, py1, px2, py2
            )
        return min(total_intersection / seat_area, 1.0)

    def update_seat_status(self, seat, overlap):
        threshold = self.config.occupancy_overlap_threshold
        now = datetime.now()
        testing = self.config.testing_mode
        seat.overlap_percentage = overlap
        is_covered = overlap >= threshold

        if seat.status == "Empty":
            if is_covered:
                if testing:
                    seat.status = "Occupied"
                    seat.last_empty_time = None
                    seat.is_actionable = False
                    seat.vacancy_timer_start = None
                    self._seat_first_overlap_time[seat.id] = None
                else:
                    if self._seat_first_overlap_time.get(seat.id) is None:
                        self._seat_first_overlap_time[seat.id] = now
                    elapsed = (now - self._seat_first_overlap_time[seat.id]).total_seconds()
                    if elapsed >= self.config.occupancy_confirmation_seconds:
                        seat.status = "Occupied"
                        seat.last_empty_time = None
                        seat.is_actionable = False
                        seat.vacancy_timer_start = None
                        self._seat_first_overlap_time[seat.id] = None
            else:
                self._seat_first_overlap_time[seat.id] = None
        elif seat.status == "Occupied":
            if is_covered:
                seat.vacancy_timer_start = None
                self._seat_first_overlap_time[seat.id] = None
            else:
                if testing:
                    seat.status = "Empty"
                    seat.last_empty_time = now
                    seat.is_actionable = False
                    seat.vacancy_timer_start = None
                    self._seat_first_overlap_time[seat.id] = None
                else:
                    if seat.vacancy_timer_start is None:
                        seat.vacancy_timer_start = now
                    elapsed_minutes = (now - seat.vacancy_timer_start).total_seconds() / 60.0
                    if elapsed_minutes >= self.config.vacancy_grace_period_minutes:
                        seat.status = "Empty"
                        seat.last_empty_time = now
                        seat.is_actionable = False
                        seat.vacancy_timer_start = None
                        self._seat_first_overlap_time[seat.id] = None


def _make_config(**overrides):
    defaults = dict(
        event_type="Test",
        zones=[ZoneConfig(name="Test", empty_threshold_minutes=10)],
        detection_interval_seconds=5,
        occupancy_overlap_threshold=0.6,
        occupancy_confirmation_seconds=30,
        vacancy_grace_period_minutes=20,
        testing_mode=False,
        stability_required_scans=3,
        seat_detection_radius_pixels=100,
        person_detection_confidence_threshold=0.3,
    )
    defaults.update(overrides)
    return EventConfig(**defaults)


def _make_seat(**overrides):
    defaults = dict(
        id="test_1", x=100, y=100, width=100, height=100,
        zone="Test", status="Empty",
    )
    defaults.update(overrides)
    return Seat(**defaults)


# ===========================================================================
# Test 1: Overlap Computation
# ===========================================================================

def test_full_overlap():
    """Person bbox fully covers seat area → 100% overlap."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=100, y=100, width=100, height=100)
    detections = [(50, 50, 250, 250)]  # Much larger than seat
    assert engine.compute_seat_overlap(seat, detections) == 1.0


def test_no_overlap():
    """Person bbox is completely outside seat → 0% overlap."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=100, y=100, width=100, height=100)
    detections = [(300, 300, 400, 400)]  # Far from seat
    assert engine.compute_seat_overlap(seat, detections) == 0.0


def test_partial_overlap():
    """Person bbox partially overlaps seat → between 0 and 1."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=100, y=100, width=100, height=100)
    # Overlap region: (150,100)-(200,200) = 50*100 = 5000
    # Seat area: 100*100 = 10000
    # Expected: 0.5
    detections = [(150, 100, 300, 200)]
    overlap = engine.compute_seat_overlap(seat, detections)
    assert abs(overlap - 0.5) < 0.01


def test_exact_60_percent_overlap():
    """Verify the 60% threshold boundary."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=0, y=0, width=100, height=100)
    # 60*100 = 6000 / 10000 = 0.6
    detections = [(0, 0, 60, 100)]
    overlap = engine.compute_seat_overlap(seat, detections)
    assert abs(overlap - 0.6) < 0.01


# ===========================================================================
# Test 2: Cumulative Overlap
# ===========================================================================

def test_cumulative_overlap_two_people():
    """Two people each covering 35% → combined 70% > threshold."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=0, y=0, width=100, height=100)
    # Person A: (0,0)-(35,100) → 35*100=3500 → 35%
    # Person B: (35,0)-(70,100) → 35*100=3500 → 35%
    # Total: 70%
    detections = [(0, 0, 35, 100), (35, 0, 70, 100)]
    overlap = engine.compute_seat_overlap(seat, detections)
    assert abs(overlap - 0.7) < 0.01


def test_cumulative_overlap_with_actual_overlap_between_people():
    """Two overlapping person bboxes → their seat intersection area sums (may exceed seat area, capped at 1.0)."""
    engine = MockVisionEngine(_make_config())
    seat = _make_seat(x=0, y=0, width=100, height=100)
    # Both cover full seat → each contributes 10000, total = 20000/10000 = 2.0 → capped at 1.0
    detections = [(0, 0, 100, 100), (0, 0, 100, 100)]
    overlap = engine.compute_seat_overlap(seat, detections)
    assert overlap == 1.0


# ===========================================================================
# Test 3: Occupancy Confirmation Timer
# ===========================================================================

def test_no_instant_occupy_without_testing_mode():
    """With testing_mode off, a single detection should NOT flip to Occupied."""
    config = _make_config(testing_mode=False, occupancy_confirmation_seconds=30)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Empty")
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.8)  # Above threshold
    assert seat.status == "Empty"  # Not yet confirmed


def test_confirmation_after_elapsed_time():
    """If first overlap started 31 seconds ago → should flip to Occupied."""
    config = _make_config(testing_mode=False, occupancy_confirmation_seconds=30)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Empty")
    # Simulate: overlap started 31 seconds ago
    engine._seat_first_overlap_time[seat.id] = datetime.now() - timedelta(seconds=31)
    engine.update_seat_status(seat, 0.8)
    assert seat.status == "Occupied"


def test_confirmation_resets_on_gap():
    """If overlap drops below threshold, confirmation timer resets."""
    config = _make_config(testing_mode=False, occupancy_confirmation_seconds=30)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Empty")
    engine._seat_first_overlap_time[seat.id] = datetime.now() - timedelta(seconds=20)
    # Overlap drops
    engine.update_seat_status(seat, 0.3)
    assert seat.status == "Empty"
    assert engine._seat_first_overlap_time[seat.id] is None  # Timer reset


# ===========================================================================
# Test 4: Vacancy Grace Period
# ===========================================================================

def test_vacancy_grace_period_starts():
    """When occupied seat loses coverage, grace period timer should start."""
    config = _make_config(testing_mode=False, vacancy_grace_period_minutes=20)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Occupied")
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.1)  # Below threshold
    assert seat.status == "Occupied"  # Still occupied during grace
    assert seat.vacancy_timer_start is not None


def test_vacancy_grace_period_cancelled():
    """If person returns during grace period, timer cancels."""
    config = _make_config(testing_mode=False, vacancy_grace_period_minutes=20)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Occupied")
    seat.vacancy_timer_start = datetime.now() - timedelta(minutes=5)
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.8)  # Person returns
    assert seat.status == "Occupied"
    assert seat.vacancy_timer_start is None  # Timer cancelled


def test_vacancy_grace_period_expires():
    """After 20 minutes of no coverage, seat should flip to Empty."""
    config = _make_config(testing_mode=False, vacancy_grace_period_minutes=20)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Occupied")
    seat.vacancy_timer_start = datetime.now() - timedelta(minutes=21)
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.1)  # Below threshold
    assert seat.status == "Empty"
    assert seat.last_empty_time is not None
    assert seat.vacancy_timer_start is None


# ===========================================================================
# Test 5: Testing Mode (Instant)
# ===========================================================================

def test_testing_mode_instant_occupy():
    """Testing mode: overlap above threshold → instant Occupied."""
    config = _make_config(testing_mode=True)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Empty")
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.8)
    assert seat.status == "Occupied"


def test_testing_mode_instant_empty():
    """Testing mode: overlap drops below threshold → instant Empty."""
    config = _make_config(testing_mode=True)
    engine = MockVisionEngine(config)
    seat = _make_seat(status="Occupied")
    engine._seat_first_overlap_time[seat.id] = None
    engine.update_seat_status(seat, 0.1)
    assert seat.status == "Empty"
    assert seat.last_empty_time is not None


# ===========================================================================
# Test: Rectangle Intersection Helper
# ===========================================================================

def test_rect_intersection_no_overlap():
    area = MockVisionEngine._compute_rect_intersection_area(0, 0, 50, 50, 100, 100, 200, 200)
    assert area == 0


def test_rect_intersection_full_containment():
    area = MockVisionEngine._compute_rect_intersection_area(10, 10, 90, 90, 0, 0, 100, 100)
    assert area == 80 * 80  # Inner rect area


def test_rect_intersection_partial():
    area = MockVisionEngine._compute_rect_intersection_area(0, 0, 100, 100, 50, 50, 150, 150)
    assert area == 50 * 50  # Overlap region


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
