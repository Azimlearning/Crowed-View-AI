"""
FastAPI backend server for Venue Intelligence AI.
"""
import os
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
import google.generativeai as genai
from typing import List

from models import (
    SeatStatusResponse, ZoneStatsResponse, SuggestionRequest, SuggestionResponse,
    ConfigUpdateRequest, Seat, Zone
)
from vision_engine import VisionEngine
from logger_config import setup_logging, get_logger

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# Cache for zone statistics (simple in-memory cache)
_zone_stats_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 2.0  # Cache for 2 seconds
}

# Load environment variables
load_dotenv()

# Initialize paths
BASE_DIR = Path(__file__).parent.parent
SEATING_MAP_PATH = BASE_DIR / "data" / "seating_map.json"
CONFIG_PATH = BASE_DIR / "data" / "config.json"

vision_engine: VisionEngine = None
# WebSocket connections manager
websocket_connections: List[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global vision_engine
    logger.info("Starting Venue Intelligence AI backend...")
    vision_engine = VisionEngine(str(SEATING_MAP_PATH), str(CONFIG_PATH))
    thread = threading.Thread(target=vision_engine.main_detection_loop, daemon=True)
    thread.start()
    logger.info("Vision engine started")
    yield
    if vision_engine:
        vision_engine.cleanup()
        logger.info("Vision engine cleaned up")


# Initialize FastAPI app
app = FastAPI(title="Venue Intelligence AI API", lifespan=lifespan)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Venue Intelligence AI API", "status": "running"}


@app.get("/api/debug-seat-map", response_class=Response)
async def debug_seat_map():
    """Return a snapshot of the camera with seat rectangles drawn (for testing camera and seat positions)."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    png = vision_engine.get_debug_frame_png()
    if not png:
        raise HTTPException(status_code=503, detail="No frame yet; wait for first detection cycle")
    return Response(content=png, media_type="image/png")


@app.get("/api/debug-detection-status")
async def debug_detection_status():
    """Get current detection status for debugging."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    seats_data = []
    for seat in vision_engine.seats.values():
        seats_data.append({
            "id": seat.id,
            "zone": seat.zone,
            "status": seat.status,
            "overlap_percentage": round(seat.overlap_percentage, 4),
            "vacancy_timer_start": str(seat.vacancy_timer_start) if seat.vacancy_timer_start else None,
            "is_actionable": seat.is_actionable,
            "last_empty_time": str(seat.last_empty_time) if seat.last_empty_time else None,
            "position": {"x": seat.x, "y": seat.y, "width": seat.width, "height": seat.height}
        })
    
    return {
        "seats": seats_data,
        "last_person_detections": vision_engine._last_person_detections if hasattr(vision_engine, '_last_person_detections') else None,
        "config": {
            "detection_interval_seconds": vision_engine.config.detection_interval_seconds,
            "occupancy_overlap_threshold": vision_engine.config.occupancy_overlap_threshold,
            "occupancy_confirmation_seconds": vision_engine.config.occupancy_confirmation_seconds,
            "vacancy_grace_period_minutes": vision_engine.config.vacancy_grace_period_minutes,
            "testing_mode": vision_engine.config.testing_mode,
            "person_detection_confidence_threshold": vision_engine.config.person_detection_confidence_threshold,
            "debug_detection": getattr(vision_engine.config, 'debug_detection', False)
        }
    }


async def _mjpeg_stream_generator():
    """Yield MJPEG frames for live camera stream with error handling."""
    import base64
    import io
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a fallback "no camera" frame
    def create_fallback_frame() -> bytes:
        """Create a fallback frame showing 'Camera Unavailable' message."""
        img = Image.new('RGB', (640, 480), color='black')
        draw = ImageDraw.Draw(img)
        try:
            # Try to use default font
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        text = "Camera Unavailable"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((640 - text_width) // 2, (480 - text_height) // 2)
        draw.text(position, text, fill='white', font=font)
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    
    fallback_frame = create_fallback_frame()
    consecutive_errors = 0
    max_errors = 10
    
    while True:
        try:
            if not vision_engine:
                await asyncio.sleep(0.5)
                continue
            
            jpeg = vision_engine.get_latest_frame_jpeg()
            if jpeg is None:
                consecutive_errors += 1
                if consecutive_errors > max_errors:
                    # Use fallback frame after too many errors
                    jpeg = fallback_frame
                else:
                    await asyncio.sleep(0.2)
                    continue
            else:
                consecutive_errors = 0  # Reset on success
            
            # Validate JPEG data
            if len(jpeg) == 0:
                jpeg = fallback_frame
            
            frame_data = (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
            )
            yield frame_data
            await asyncio.sleep(0.05)  # ~20 fps for smooth live feed
            
        except Exception as e:
            # Log error and yield fallback frame
            logger.error(f"Error in camera stream: {e}", exc_info=True)
            consecutive_errors += 1
            try:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(fallback_frame)).encode() + b"\r\n\r\n" + fallback_frame + b"\r\n"
                )
            except:
                pass  # If even fallback fails, skip this frame
            await asyncio.sleep(0.5)  # Wait longer on error


@app.get("/api/camera-stream")
async def camera_stream():
    """Live MJPEG stream of webcam with seat overlay (for dashboard embed)."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    return StreamingResponse(
        _mjpeg_stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/seats", response_model=SeatStatusResponse)
async def get_seats():
    """Get current status of all seats."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    seats = vision_engine.get_all_seats()
    return SeatStatusResponse(seats=list(seats.values()))


@app.get("/api/zones", response_model=list[ZoneStatsResponse])
async def get_zones():
    """Get statistics for all zones (cached for 2 seconds)."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    import time
    current_time = time.time()
    
    # Check cache validity
    if (_zone_stats_cache['data'] is not None and 
        current_time - _zone_stats_cache['timestamp'] < _zone_stats_cache['ttl']):
        return _zone_stats_cache['data']
    
    # Calculate zone stats
    zones = vision_engine.get_zones()
    zone_stats = []
    
    for zone_name, zone in zones.items():
        total_seats = len(zone.seats)
        occupied_seats = sum(1 for seat in zone.seats if seat.status == "Occupied")
        empty_seats = total_seats - occupied_seats
        actionable_seats = sum(1 for seat in zone.seats if seat.is_actionable)
        empty_percentage = (empty_seats / total_seats * 100) if total_seats > 0 else 0
        
        zone_stats.append(ZoneStatsResponse(
            zone_name=zone_name,
            total_seats=total_seats,
            occupied_seats=occupied_seats,
            empty_seats=empty_seats,
            actionable_seats=actionable_seats,
            empty_percentage=round(empty_percentage, 2)
        ))
    
    # Update cache
    _zone_stats_cache['data'] = zone_stats
    _zone_stats_cache['timestamp'] = current_time
    
    return zone_stats


@app.websocket("/ws/seats")
async def websocket_seats(websocket: WebSocket):
    """WebSocket endpoint for real-time seat updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(websocket_connections)}")
    
    try:
        while True:
            # Send current seat status every second
            if vision_engine:
                seats = vision_engine.get_all_seats()
                await websocket.send_json({
                    "type": "seats_update",
                    "seats": [seat.model_dump() for seat in seats.values()]
                })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(websocket_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


@app.post("/api/config")
async def update_config(request: ConfigUpdateRequest):
    """Update runtime configuration (overlap threshold, timers, testing mode)."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No configuration values provided")
    
    vision_engine.update_config(**updates)
    
    return {
        "message": "Configuration updated",
        "updated_fields": list(updates.keys()),
        "current_config": {
            "occupancy_overlap_threshold": vision_engine.config.occupancy_overlap_threshold,
            "occupancy_confirmation_seconds": vision_engine.config.occupancy_confirmation_seconds,
            "vacancy_grace_period_minutes": vision_engine.config.vacancy_grace_period_minutes,
            "testing_mode": vision_engine.config.testing_mode,
            "detection_interval_seconds": vision_engine.config.detection_interval_seconds,
        }
    }


@app.get("/api/config")
async def get_config():
    """Get current runtime configuration."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    return {
        "occupancy_overlap_threshold": vision_engine.config.occupancy_overlap_threshold,
        "occupancy_confirmation_seconds": vision_engine.config.occupancy_confirmation_seconds,
        "vacancy_grace_period_minutes": vision_engine.config.vacancy_grace_period_minutes,
        "testing_mode": vision_engine.config.testing_mode,
        "detection_interval_seconds": vision_engine.config.detection_interval_seconds,
        "person_detection_confidence_threshold": vision_engine.config.person_detection_confidence_threshold,
        "debug_detection": vision_engine.config.debug_detection,
    }


@app.post("/api/suggestions", response_model=SuggestionResponse)
async def get_suggestions(request: SuggestionRequest):
    """Get AI-generated suggestions for a zone."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    # Get zone data
    zones = vision_engine.get_zones()
    zone = zones.get(request.zone_name)
    
    if not zone:
        raise HTTPException(status_code=404, detail=f"Zone '{request.zone_name}' not found")
    
    # Calculate zone statistics
    total_seats = len(zone.seats)
    empty_seats = sum(1 for seat in zone.seats if seat.status == "Empty")
    actionable_seats = [seat for seat in zone.seats if seat.is_actionable]
    
    if total_seats == 0:
        raise HTTPException(status_code=400, detail="Zone has no seats")
    
    empty_percentage = (empty_seats / total_seats) * 100
    
    # Calculate average empty duration for actionable seats
    if actionable_seats:
        current_time = datetime.now()
        empty_durations = [
            (current_time - seat.last_empty_time).total_seconds() / 60
            for seat in actionable_seats
            if seat.last_empty_time
        ]
        avg_empty_duration = sum(empty_durations) / len(empty_durations) if empty_durations else 0
    else:
        avg_empty_duration = zone.empty_threshold_minutes
    
    # Load event config
    with open(CONFIG_PATH, 'r') as f:
        config_data = json.load(f)
    event_type = config_data.get('event_type', 'Event')
    
    # Generate suggestions using Gemini API
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = (
            f"The event is a {event_type}. In the {request.zone_name} zone, "
            f"{empty_percentage:.1f}% of seats are currently Empty. "
            f"These seats have exceeded the {zone.empty_threshold_minutes}-minute vacancy threshold "
            f"and have been empty for an average of {avg_empty_duration:.1f} minutes. "
            f"Given our goal to maximize venue optics and recover lost ticketing revenue "
            f"without moving physical furniture, provide 2-3 specific, actionable operational "
            f"suggestions (e.g., offering seat upgrades to waiting list guests, moving back-row "
            f"attendees forward, contacting VIP concierge). "
            f"Format your response as a simple numbered list, one suggestion per line."
        )
        
        response = model.generate_content(prompt)
        suggestions_text = response.text.strip()
        
        # Parse suggestions (split by newlines and clean up)
        suggestions = [
            line.strip('- ').strip()
            for line in suggestions_text.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        
        # Ensure we have at least 2-3 suggestions
        if len(suggestions) < 2:
            # Fallback: split by periods if needed
            suggestions = [s.strip() for s in suggestions_text.split('.') if s.strip()][:3]
        
        return SuggestionResponse(
            zone_name=request.zone_name,
            suggestions=suggestions[:3],  # Limit to 3 suggestions
            empty_percentage=round(empty_percentage, 2),
            empty_duration_minutes=round(avg_empty_duration, 2)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
