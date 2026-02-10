import React, { useState } from 'react';
import './SeatGrid.css';

const SeatGrid = ({ seats, onSeatClick }) => {
  const [hoveredSeat, setHoveredSeat] = useState(null);

  // Group seats by zone
  const seatsByZone = {};
  seats.forEach(seat => {
    if (!seatsByZone[seat.zone]) {
      seatsByZone[seat.zone] = [];
    }
    seatsByZone[seat.zone].push(seat);
  });

  const getSeatColor = (seat) => {
    if (seat.is_actionable) {
      return '#ff9800'; // Orange for actionable
    }
    // Green = Empty, Red = Occupied (seat taken)
    return seat.status === 'Empty' ? '#4caf50' : '#f44336';
  };

  const getSeatIcon = (seat) => {
    if (seat.is_actionable) {
      return '⚠️';
    }
    return seat.status === 'Empty' ? '🟢' : '🔴';
  };

  const formatTooltip = (seat) => {
    const parts = [
      `Seat: ${seat.id}`,
      `Status: ${seat.status}`,
      `Zone: ${seat.zone}`
    ];
    if (seat.is_actionable && seat.last_empty_time) {
      const emptyDuration = Math.floor((new Date() - new Date(seat.last_empty_time)) / 60000);
      parts.push(`Empty for: ${emptyDuration} minutes`);
      parts.push('Click for AI suggestions');
    }
    return parts.join('\n');
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
            {zoneSeats.map(seat => (
              <div
                key={seat.id}
                className={`seat ${seat.is_actionable ? 'actionable' : ''} ${hoveredSeat === seat.id ? 'hovered' : ''}`}
                style={{
                  backgroundColor: getSeatColor(seat),
                  cursor: seat.is_actionable ? 'pointer' : 'default',
                  position: 'relative',
                  padding: '12px',
                  borderRadius: '8px',
                  boxShadow: hoveredSeat === seat.id ? '0 4px 8px rgba(0,0,0,0.3)' : '0 2px 4px rgba(0,0,0,0.2)',
                  transition: 'all 0.2s ease',
                  minHeight: '80px',
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
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SeatGrid;
