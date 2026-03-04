# JSON Data Schema

## Input Shape

### Seat (from `seating_map.json`)
```json
{
  "id": "string",
  "x": "int (px, top-left)",
  "y": "int (px, top-left)",
  "width": "int (px, default 100)",
  "height": "int (px, default 100)"
}
```

### EventConfig (from `config.json`)
```json
{
  "event_type": "string",
  "zones": [{"name": "string", "empty_threshold_minutes": "int"}],
  "detection_interval_seconds": "int (default 7)",
  "occupancy_overlap_threshold": "float (0.0-1.0, default 0.6)",
  "occupancy_confirmation_seconds": "int (default 30)",
  "vacancy_grace_period_minutes": "int (default 20)",
  "testing_mode": "bool (default false)",
  "person_detection_confidence_threshold": "float (default 0.3)",
  "debug_detection": "bool (default false)"
}
```

## Output Shape (Payload)

### Seat Status (`/api/seats`)
```json
{
  "seats": [{
    "id": "string",
    "x": "int", "y": "int",
    "width": "int", "height": "int",
    "zone": "string",
    "status": "'Occupied' | 'Empty'",
    "overlap_percentage": "float (0.0-1.0)",
    "vacancy_timer_start": "datetime | null",
    "last_empty_time": "datetime | null",
    "is_actionable": "bool"
  }]
}
```

### Config (`/api/config`)
```json
{
  "occupancy_overlap_threshold": "float",
  "occupancy_confirmation_seconds": "int",
  "vacancy_grace_period_minutes": "int",
  "testing_mode": "bool",
  "detection_interval_seconds": "int"
}
```

---
# Maintenance Log
- 2026-03-04: Replaced circle-based overlap + stability counter with area-based 60% overlap + temporal confirmation (30s) + vacancy grace period (20min). Added testing mode bypass. Updated calibration tool to rectangles.
