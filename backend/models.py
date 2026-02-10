"""
Data models for Venue Intelligence AI system.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Seat(BaseModel):
    """Represents a single seat in the venue."""
    id: str
    x: int = Field(description="X coordinate in camera pixel space")
    y: int = Field(description="Y coordinate in camera pixel space")
    zone: str = Field(description="Zone name this seat belongs to")
    status: str = Field(default="Empty", description="Current status: 'Occupied' or 'Empty'")
    stability_counter: int = Field(default=0, description="Consecutive scans with same status")
    last_empty_time: Optional[datetime] = Field(default=None, description="Timestamp when seat became empty")
    is_actionable: bool = Field(default=False, description="True if empty for longer than threshold")


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
    detection_interval_seconds: int
    stability_required_scans: int
    seat_detection_radius_pixels: int
    person_detection_confidence_threshold: float = Field(default=0.3, description="YOLO confidence threshold for person detection (0.25-0.5)")
    debug_detection: bool = Field(default=False, description="Log detection details to console")
    use_hysteresis: bool = Field(default=False, description="Use score-based hysteresis to reduce boundary flicker")
    hysteresis_occupied_threshold: int = Field(default=3, description="Score threshold to switch Empty -> Occupied (when use_hysteresis)")
    hysteresis_empty_threshold: int = Field(default=-3, description="Score threshold to switch Occupied -> Empty (when use_hysteresis)")


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
