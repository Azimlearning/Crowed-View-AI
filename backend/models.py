"""
Data models for Venue Intelligence AI system.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Seat(BaseModel):
    """Represents a single seat in the venue."""
    id: str
    x: int = Field(description="X coordinate in camera pixel space (top-left of seat area)")
    y: int = Field(description="Y coordinate in camera pixel space (top-left of seat area)")
    width: int = Field(default=100, description="Width of seat area in pixels")
    height: int = Field(default=100, description="Height of seat area in pixels")
    zone: str = Field(description="Zone name this seat belongs to")
    status: str = Field(default="Empty", description="Current status: 'Occupied' or 'Empty'")
    stability_counter: int = Field(default=0, description="(Deprecated) Consecutive scans with same status")
    last_empty_time: Optional[datetime] = Field(default=None, description="Timestamp when seat became empty")
    is_actionable: bool = Field(default=False, description="True if empty for longer than threshold")
    overlap_percentage: float = Field(default=0.0, description="Current cumulative overlap percentage (0.0-1.0)")
    vacancy_timer_start: Optional[datetime] = Field(default=None, description="When person left; seat stays Occupied for grace period")


class Zone(BaseModel):
    """Represents a zone with multiple seats."""
    name: str
    seats: List[Seat] = Field(default_factory=list)
    empty_threshold_minutes: int = Field(description="Minutes before empty seat becomes actionable")


class ZoneConfig(BaseModel):
    """Configuration for a zone."""
    name: str
    empty_threshold_minutes: int


class EventConfig(BaseModel):
    """Event configuration settings."""
    event_type: str
    zones: List[ZoneConfig]
    detection_interval_seconds: int = Field(default=7)

    # --- New area-overlap & temporal parameters ---
    occupancy_overlap_threshold: float = Field(default=0.6, description="Fraction of seat area that must be covered (0.0-1.0)")
    occupancy_confirmation_seconds: int = Field(default=30, description="Seconds of sustained overlap before status flips to Occupied")
    vacancy_grace_period_minutes: int = Field(default=20, description="Minutes seat stays Occupied after person leaves")
    testing_mode: bool = Field(default=False, description="Bypass all timers for instant status changes")

    # --- Deprecated (kept for backward compat) ---
    stability_required_scans: int = Field(default=3, description="(Deprecated) Use occupancy_confirmation_seconds instead")
    seat_detection_radius_pixels: int = Field(default=100, description="(Deprecated) Use seat width/height instead")

    person_detection_confidence_threshold: float = Field(default=0.3, description="YOLO confidence threshold for person detection (0.25-0.5)")
    debug_detection: bool = Field(default=False, description="Log detection details to console")

    # --- Deprecated hysteresis (kept for backward compat) ---
    use_hysteresis: bool = Field(default=False, description="(Deprecated)")
    hysteresis_occupied_threshold: int = Field(default=3, description="(Deprecated)")
    hysteresis_empty_threshold: int = Field(default=-3, description="(Deprecated)")


class SeatStatusResponse(BaseModel):
    """API response for seat status."""
    seats: List[Seat]


class ZoneStatsResponse(BaseModel):
    """API response for zone statistics."""
    zone_name: str
    total_seats: int
    occupied_seats: int
    empty_seats: int
    actionable_seats: int
    empty_percentage: float


class SuggestionRequest(BaseModel):
    """Request body for AI suggestions."""
    zone_name: str


class SuggestionResponse(BaseModel):
    """Response containing AI-generated suggestions."""
    zone_name: str
    suggestions: List[str]
    empty_percentage: float
    empty_duration_minutes: float


class ConfigUpdateRequest(BaseModel):
    """Request body for runtime config updates."""
    occupancy_overlap_threshold: Optional[float] = None
    occupancy_confirmation_seconds: Optional[int] = None
    vacancy_grace_period_minutes: Optional[int] = None
    testing_mode: Optional[bool] = None
    detection_interval_seconds: Optional[int] = None
