import React, { useState } from 'react';
import './SeatGrid.css';

const SeatGrid = ({ seats, onSeatClick, config }) => {
  const [hoveredSeat, setHoveredSeat] = useState(null);

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
          <div className="seat-grid" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
            gap: '12px',
            padding: '16px'
          }}>
            {zoneSeats.map(seat => {
              const countdown = getGraceCountdown(seat);
              const confirmProg = getConfirmationProgress(seat);
              const aspectRatio = getSeatAspectRatio(seat);

              return (
                <div
                  key={seat.id}
                  className={getSeatClasses(seat)}
                  style={{
                    backgroundColor: getSeatColor(seat),
                    cursor: seat.is_actionable ? 'pointer' : 'default',
                    position: 'relative',
                    padding: '12px',
                    borderRadius: '8px',
                    boxShadow: hoveredSeat === seat.id ? '0 4px 8px rgba(0,0,0,0.3)' : '0 2px 4px rgba(0,0,0,0.2)',
                    transition: 'all 0.2s ease',
                    minHeight: '80px',
                    aspectRatio: `${aspectRatio}`,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold'
                  }}
                  title={formatTooltip(seat)}
                  onMouseEnter={() => setHoveredSeat(seat.id)}
                  onMouseLeave={() => setHoveredSeat(null)}
                  onClick={() => seat.is_actionable && onSeatClick && onSeatClick(seat)}
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
