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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI
from typing import List
import cv2
import numpy as np
import base64

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

# Initialize paths
BASE_DIR = Path(__file__).parent.parent
SEATING_MAP_PATH = BASE_DIR / "data" / "seating_map.json"
CONFIG_PATH = BASE_DIR / "data" / "config.json"

# Load environment variables from project root
load_dotenv(BASE_DIR / ".env")

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

# Serve the data directory at /static so the frontend can fetch layout_background.jpg
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "data")), name="static")

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
                payload = jsonable_encoder({
                    "type": "seats_update",
                    "seats": [seat.model_dump() for seat in seats.values()]
                })
                await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(websocket_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

@app.post("/api/seating-map")
async def update_seating_map(request: dict):
    """Update seating map on disk and hot-reload vision engine."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    if "zones" not in request:
        raise HTTPException(status_code=400, detail="Payload must contain 'zones'")
        
    try:
        # Save to disk
        with open(SEATING_MAP_PATH, 'w') as f:
            json.dump(request, f, indent=2)
            
        # Hot-reload vision engine
        vision_engine.reload_seating_map()
        
        return {"message": "Seating map updated successfully"}
    except Exception as e:
        logger.error(f"Error updating seating map: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auto-calibrate")
async def auto_calibrate(strategy: str = Query("auto", description="Strategy: auto, gemini, opencv")):
    """Analyze the current frame and return candidate seat bounding boxes."""
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")
    
    jpeg_bytes = vision_engine.get_latest_raw_frame_jpeg()
    if not jpeg_bytes:
        raise HTTPException(status_code=503, detail="No camera frame available")
        
    # --- Primary: Gemini API ---
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key and strategy in ("auto", "gemini"):
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
            )
            
            prompt = (
                "Analyze this 640x480 venue image. Detect all individual seating positions (empty or occupied chairs, stools, benches). "
                "Return a raw JSON array of exact bounding boxes representing each unique seat: "
                "[{\"x\": int, \"y\": int, \"width\": int, \"height\": int}]. "
                "Exclude tables and floors, just the seats. "
                "Output ONLY the raw JSON list without markdown formatting or code blocks."
            )
            
            base64_img = base64.b64encode(jpeg_bytes).decode('utf-8')
            
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-lite-preview-02-05:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_img}"
                                }
                            }
                        ]
                    }
                ]
            )
            
            text = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            boxes = json.loads(text)
            
            valid_boxes = [b for b in boxes if all(k in b for k in ('x', 'y', 'width', 'height'))]
            if valid_boxes:
                logger.info(f"OpenRouter auto-calibration found {len(valid_boxes)} seats")
                return {"source": "gemini", "boxes": valid_boxes}
        except Exception as e:
            logger.warning(f"OpenRouter auto-calibration failed: {e}. Falling back to OpenCV.")
            if strategy == "gemini":
                # If explicitly asked for gemini and it failed, we could throw,
                # but fallback is safer for demos.
                pass
            
    # --- Fallback: OpenCV ---
    try:
        nparr = np.frombuffer(jpeg_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if 2000 < area < 40000 and 10 < w < 300 and 10 < h < 300:
                boxes.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
                
        logger.info(f"OpenCV fallback found {len(boxes)} seats")
        return {"source": "opencv", "boxes": boxes}
    except Exception as e:
        logger.error(f"Auto-calibration completely failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to detect seats")

@app.post("/api/upload-layout-image")
async def upload_layout_image(file: UploadFile = File(...)):
    """Accept an uploaded image and run Gemini bounding box extraction on it.
    
    The image can be any size; Gemini normalizes coordinates relative to image dimensions.
    The frontend should scale the returned boxes to match the canvas dimensions.
    """
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
    
    # Validate image content type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.")
        
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured. Add OPENROUTER_API_KEY to your .env file.")

    try:
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image.")
        img_h, img_w = img.shape[:2]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode error: {e}")
        
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )
        
        prompt = (
            f"Analyze this venue layout image ({img_w}x{img_h} pixels). "
            "Detect all individual seating positions (chairs, stools, benches — both empty and occupied). "
            f"Return a raw JSON array of bounding boxes in pixel coordinates for this exact image size: "
            "[{\"x\": int, \"y\": int, \"width\": int, \"height\": int}]. "
            "x and y are the top-left corner. Exclude tables, floors, and standing areas — just the seats. "
            "Output ONLY the raw JSON list without any markdown or code block wrappers."
        )
        
        base64_img = base64.b64encode(contents).decode('utf-8')
        mime_type = file.content_type or "image/jpeg"
        
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_img}"
                            }
                        }
                    ]
                }
            ]
        )
        
        text = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        boxes = json.loads(text)
        
        valid_boxes = [b for b in boxes if all(k in b for k in ('x', 'y', 'width', 'height'))]
        logger.info(f"Upload layout: OpenRouter detected {len(valid_boxes)} seats in {img_w}x{img_h} image")
        return {
            "source": "gemini",
            "boxes": valid_boxes,
            "image_width": img_w,
            "image_height": img_h,
        }
    except Exception as e:
        logger.error(f"Upload layout gemini analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Layout analysis failed: {str(e)}")


@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    """Save an uploaded image as the venue reference background.
    
    The image is saved to data/layout_background.jpg and served at /static/layout_background.jpg.
    The frontend can display this image behind the seat canvas for assisted manual placement.
    No AI detection is run — this is purely for visual reference.
    """
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}")
    
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
    
    # Decode then re-encode as JPEG (normalises PNG/WebP to a single consistent format)
    try:
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image.")
        img_h, img_w = img.shape[:2]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode error: {e}")
    
    dest_path = BASE_DIR / "data" / "layout_background.jpg"
    success, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode image as JPEG")
    
    with open(dest_path, "wb") as f:
        f.write(buf.tobytes())
    
    logger.info(f"Background image saved: {img_w}x{img_h} → {dest_path}")
    return {
        "message": "Background image saved successfully",
        "url": "/static/layout_background.jpg",
        "image_width": img_w,
        "image_height": img_h,
    }


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

@app.get("/api/analytics/events")
async def get_analytics_events(limit: int = 50):
    """Return the most recent seat change events from the SQLite log (debug/review)."""
    import db_logger as _db
    return {"events": _db.get_recent_events(limit=limit)}


@app.post("/api/analytics/insights")
async def get_analytics_insights():
    """Generate an AI-powered trend analysis report using in-session history snapshots.
    
    Bundles the in-memory history_snapshots (zone occupancy over time) and sends
    them to Gemini 1.5 Flash for timeline-aware operational insights.
    """
    if not vision_engine:
        raise HTTPException(status_code=503, detail="Vision engine not initialized")

    snapshots = vision_engine.history_snapshots
    current_zones = vision_engine.get_zones()

    # Build current snapshot summary for Gemini context
    current_summary_lines = []
    for zone_name, zone in current_zones.items():
        total = len(zone.seats)
        occupied = sum(1 for s in zone.seats if s.status == "Occupied")
        actionable = sum(1 for s in zone.seats if s.is_actionable)
        empty_pct = round((total - occupied) / total * 100, 1) if total > 0 else 0.0
        current_summary_lines.append(
            f"  - {zone_name}: {occupied}/{total} occupied ({100-empty_pct:.1f}% fill rate), "
            f"{actionable} actionable seat(s)"
        )
    current_summary = "\n".join(current_summary_lines)

    # Build snapshot timeline string (last 12 snapshots = 1 hour at 5-min intervals)
    recent_snapshots = snapshots[-12:] if len(snapshots) > 12 else snapshots
    if recent_snapshots:
        timeline_lines = []
        for snap in recent_snapshots:
            ts = snap["timestamp"]
            zone_parts = ", ".join(
                f"{z['zone_name']}: {z['occupied_seats']}/{z['total_seats']} occupied"
                for z in snap["zones"]
            )
            timeline_lines.append(f"  [{ts}] {zone_parts}")
        timeline_str = "\n".join(timeline_lines)
        timeline_context = f"Occupancy timeline (last {len(recent_snapshots)} snapshots, 5-min intervals):\n{timeline_str}"
    else:
        timeline_context = "No historical snapshots yet (system started recently — analytics based on current state only)."

    # Load event type from config
    with open(CONFIG_PATH, 'r') as f:
        config_data = json.load(f)
    event_type = config_data.get('event_type', 'Event')

    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        prompt = (
            f"You are an AI Venue Intelligence Analyst for a live {event_type}. "
            f"Your job is to synthesize real-time and historical seat occupancy data into "
            f"a concise, actionable analytics report for a venue manager.\n\n"
            f"## Current State\n{current_summary}\n\n"
            f"## {timeline_context}\n\n"
            f"## Your Task\n"
            f"Write a short operational analytics report (3-5 sentences max) covering:\n"
            f"1. **Trend**: Is occupancy rising, stable, or declining compared to earlier?\n"
            f"2. **Hotspots**: Which zone needs the most immediate attention and why?\n"
            f"3. **Recommendation**: One specific, high-priority action the venue manager should take right now.\n\n"
            f"Keep the tone professional and data-driven. Do not use markdown headers — plain readable text only."
        )

        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[{"role": "user", "content": prompt}]
        )
        insight_text = response.choices[0].message.content.strip()

        return {
            "insight": insight_text,
            "snapshot_count": len(snapshots),
            "current_summary": current_summary,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    except Exception as e:
        logger.error(f"Analytics insights generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")


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
    
    # Generate suggestions using OpenRouter
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )
        
        prompt = (
            f"You are an AI assistant for a Smart Building Management system. "
            f"The facility is a {event_type}. In the '{request.zone_name}' zone, "
            f"{empty_percentage:.1f}% of seats are currently unoccupied. "
            f"These seats have been empty for an average of {avg_empty_duration:.1f} minutes, "
            f"exceeding the zone's {zone.empty_threshold_minutes}-minute vacancy threshold. "
            f"\n\nProvide exactly 3 concise, actionable operational suggestions. "
            f"Your suggestions MUST cover BOTH of these two areas:\n"
            f"1. **Energy Sustainability**: Actions to reduce energy waste in the empty zone "
            f"(e.g., adjusting HVAC load, dimming or switching off lighting in unoccupied sections, "
            f"reducing cooling or heating to save electricity).\n"
            f"2. **Smart Venue Management**: Actions to optimize space usage or redirect people "
            f"(e.g., consolidating attendees into occupied sections, notifying staff to close off "
            f"the empty area, or re-routing incoming visitors).\n\n"
            f"Format your response as a simple numbered list (1., 2., 3.), one suggestion per line. "
            f"Each suggestion must start with the category in brackets, e.g. [Energy] or [Venue]."
        )
        
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=[{"role": "user", "content": prompt}]
        )
        suggestions_text = response.choices[0].message.content.strip()
        
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
