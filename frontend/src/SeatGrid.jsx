import React, { useState, useEffect, useRef } from 'react';
import './SeatGrid.css';

const SeatGrid = ({ seats, onSeatClick, config, isEditingLayout }) => {
  const [hoveredSeat, setHoveredSeat] = useState(null);
  const [layout, setLayout] = useState({});
  const [draggingSeat, setDraggingSeat] = useState(null);

  const gridRef = useRef(null);

  const overlapThreshold = config?.occupancy_overlap_threshold ?? 0.6;
  const gracePeriodMinutes = config?.vacancy_grace_period_minutes ?? 20;
  const confirmationSeconds = config?.occupancy_confirmation_seconds ?? 30;

  // Group seats by zone
  const seatsByZone = {};
  seats.forEach(seat => {
    if (!seatsByZone[seat.zone]) {
      seatsByZone[seat.zone] = [];
    }
    seatsByZone[seat.zone].push(seat);
  });

  // Load layout from local storage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('crowdview_layout_v1');
      if (saved) {
        setLayout(JSON.parse(saved));
      }
    } catch (e) {
      console.error('Error loading layout', e);
    }
  }, []);

  // Pointer events for drag and drop
  const handlePointerDown = (e, seatId) => {
    if (!isEditingLayout) return;

    // Prevent default to avoid selection issues while dragging
    e.preventDefault();

    // Store starting position of the pointer and the current seat position
    const startX = e.clientX;
    const startY = e.clientY;

    // Get current position or default to 0,0
    const currentPos = layout[seatId] || { x: 0, y: 0 };

    setDraggingSeat({
      id: seatId,
      startX,
      startY,
      initialX: currentPos.x,
      initialY: currentPos.y
    });
  };

  const handlePointerMove = (e) => {
    if (!isEditingLayout || !draggingSeat) return;

    const dx = e.clientX - draggingSeat.startX;
    const dy = e.clientY - draggingSeat.startY;

    // Optional: add grid snapping by rounding dx/dy here

    setLayout(prev => ({
      ...prev,
      [draggingSeat.id]: {
        x: draggingSeat.initialX + dx,
        y: draggingSeat.initialY + dy
      }
    }));
  };

  const handlePointerUp = () => {
    if (!draggingSeat) return;

    // Save to local storage
    try {
      localStorage.setItem('crowdview_layout_v1', JSON.stringify(layout));
    } catch (e) {
      console.error('Error saving layout', e);
    }

    setDraggingSeat(null);
  };

  const getSeatColor = (seat) => {
    if (seat.is_actionable) return '#ff9800'; // Orange
    if (seat.status === 'Occupied') return '#f44336'; // Red
    return '#9e9e9e'; // Grey
  };

  const getSeatClasses = (seat) => {
    const classes = ['seat'];
    if (seat.is_actionable) classes.push('actionable');
    if (hoveredSeat === seat.id) classes.push('hovered');
    // Yellow pulse: person detected but 30s confirmation not yet complete
    const isDetecting = seat.status === 'Empty' && seat.overlap_percentage >= overlapThreshold;
    if (isDetecting) classes.push('detecting');
    return classes.join(' ');
  };

  const getGraceCountdown = (seat) => {
    if (!seat.vacancy_timer_start || seat.status !== 'Occupied') return null;
    const elapsed = (new Date() - new Date(seat.vacancy_timer_start)) / 60000;
    const remaining = Math.max(0, gracePeriodMinutes - elapsed);
    return remaining > 0 ? `-${remaining.toFixed(0)}m` : null;
  };

  const getConfirmationProgress = (seat) => {
    // Show progress only when detecting (Empty but overlap >= threshold)
    if (seat.status !== 'Empty' || seat.overlap_percentage < overlapThreshold) return null;
    // We don't have first_overlap_time on client, so show a static indicator
    return `${(seat.overlap_percentage * 100).toFixed(0)}% overlap`;
  };

  const getSeatIcon = (seat) => {
    if (seat.is_actionable) return '⚠️';
    if (seat.status === 'Occupied') return '🔴';
    if (seat.overlap_percentage >= overlapThreshold) return '🟡'; // Detecting
    return '⬜';
  };

  const formatTooltip = (seat) => {
    const overlapPct = seat.overlap_percentage != null
      ? (seat.overlap_percentage * 100).toFixed(1)
      : '0.0';
    const parts = [
      `Seat: ${seat.id}`,
      `Status: ${seat.status}`,
      `Zone: ${seat.zone}`,
      `Overlap: ${overlapPct}%`
    ];
    if (seat.status === 'Empty' && seat.overlap_percentage >= overlapThreshold) {
      parts.push(`⏳ Confirming occupancy (needs ${confirmationSeconds}s sustained)...`);
    }
    if (seat.vacancy_timer_start && seat.status === 'Occupied') {
      const countdown = getGraceCountdown(seat);
      parts.push(`🕐 Grace period active${countdown ? ` — ${countdown} until vacant` : ''}`);
    }
    if (seat.is_actionable && seat.last_empty_time) {
      const emptyDuration = Math.floor((new Date() - new Date(seat.last_empty_time)) / 60000);
      parts.push(`Empty for: ${emptyDuration} minutes`);
      parts.push('Click for AI suggestions');
    }
    return parts.join('\n');
  };

  // Compute aspect ratio from seat width/height if available
  const getSeatAspectRatio = (seat) => {
    if (seat.width && seat.height && seat.width > 0 && seat.height > 0) {
      return seat.width / seat.height;
    }
    return 1; // Default square
  };

  return (
    <div className="seat-grid-container">
      {Object.entries(seatsByZone).map(([zoneName, zoneSeats]) => (
        <div key={zoneName} className="zone-section">
          <h2 className="zone-title">{zoneName} Zone ({zoneSeats.length} seats)</h2>
          <div
            className="seat-grid"
            ref={gridRef}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
            style={{
              position: 'relative',
              minHeight: '600px', // Ensure enough space for absolute positioning
              touchAction: 'none' // Prevent scrolling while dragging on touch devices
            }}>
            {zoneSeats.map((seat, index) => {
              const countdown = getGraceCountdown(seat);
              const confirmProg = getConfirmationProgress(seat);
              const aspectRatio = getSeatAspectRatio(seat);

              return (
                <div
                  key={seat.id}
                  className={getSeatClasses(seat)}
                  style={{
                    backgroundColor: getSeatColor(seat),
                    cursor: isEditingLayout ? (draggingSeat?.id === seat.id ? 'grabbing' : 'grab') : (seat.is_actionable ? 'pointer' : 'default'),
                    position: 'absolute',
                    // If we have a saved layout, use it. Otherwise, generate a default grid fallback.
                    left: layout[seat.id] ? `${layout[seat.id].x}px` : `${(index % 8) * 130 + 16}px`,
                    top: layout[seat.id] ? `${layout[seat.id].y}px` : `${Math.floor(index / 8) * 130 + 16}px`,
                    width: '120px',
                    height: '120px',
                    padding: '12px',
                    borderRadius: '8px',
                    boxShadow: (hoveredSeat === seat.id || draggingSeat?.id === seat.id) ? '0 4px 16px rgba(0,0,0,0.4)' : '0 2px 4px rgba(0,0,0,0.2)',
                    transition: draggingSeat?.id === seat.id ? 'none' : 'box-shadow 0.2s, background-color 0.2s', // Disable position transition while dragging
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold',
                    zIndex: draggingSeat?.id === seat.id ? 100 : (hoveredSeat === seat.id ? 50 : 1),
                    userSelect: 'none' // Prevent text selection during drag
                  }}
                  title={isEditingLayout ? 'Drag to reposition' : formatTooltip(seat)}
                  onMouseEnter={() => setHoveredSeat(seat.id)}
                  onMouseLeave={() => setHoveredSeat(null)}
                  onClick={() => !isEditingLayout && seat.is_actionable && onSeatClick && onSeatClick(seat)}
                  onPointerDown={(e) => handlePointerDown(e, seat.id)}
                >
                  <span style={{ fontSize: '20px', marginBottom: '4px' }}>
                    {getSeatIcon(seat)}
                  </span>
                  <span className="seat-id" style={{ fontSize: '12px', textAlign: 'center' }}>
                    {seat.id}
                  </span>
                  <span style={{ fontSize: '10px', opacity: 0.9, marginTop: '2px' }}>
                    {seat.overlap_percentage != null
                      ? `${(seat.overlap_percentage * 100).toFixed(0)}%`
                      : '0%'}
                  </span>

                  {/* Grace period countdown */}
                  {countdown && (
                    <span style={{
                      fontSize: '10px',
                      marginTop: '2px',
                      backgroundColor: 'rgba(0,0,0,0.3)',
                      borderRadius: '4px',
                      padding: '1px 4px'
                    }}>
                      {countdown}
                    </span>
                  )}

                  {/* Confirmation progress hint */}
                  {confirmProg && !countdown && (
                    <span style={{
                      fontSize: '9px',
                      marginTop: '2px',
                      color: '#ffeb3b',
                      opacity: 0.95
                    }}>
                      {confirmProg}
                    </span>
                  )}

                  {seat.is_actionable && (
                    <span className="actionable-badge" style={{
                      position: 'absolute',
                      top: '4px',
                      right: '4px',
                      backgroundColor: 'rgba(255,255,255,0.9)',
                      color: '#ff9800',
                      borderRadius: '50%',
                      width: '20px',
                      height: '20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      !
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SeatGrid;
