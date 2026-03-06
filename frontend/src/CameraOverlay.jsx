import React, { useState, useRef, useEffect } from 'react';
import './CameraOverlay.css';

const NATIVE_WIDTH = 640;
const NATIVE_HEIGHT = 480;

const CameraOverlay = ({ seats = [], onSeatClick, config }) => {
    const containerRef = useRef(null);
    const [scale, setScale] = useState({ x: 1, y: 1 });
    const [hoveredSeat, setHoveredSeat] = useState(null);
    const [streamError, setStreamError] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    const overlapThreshold = config?.occupancy_overlap_threshold ?? 0.6;
    const gracePeriodMinutes = config?.vacancy_grace_period_minutes ?? 20;
    const confirmationSeconds = config?.occupancy_confirmation_seconds ?? 30;

    useEffect(() => {
        if (!containerRef.current) return;

        const observer = new ResizeObserver(entries => {
            for (let entry of entries) {
                const { width, height } = entry.contentRect;
                // Calculate scale factors based on actual rendered size vs native camera size
                setScale({
                    x: width / NATIVE_WIDTH,
                    y: height / NATIVE_HEIGHT
                });
            }
        });

        observer.observe(containerRef.current);

        // Initial measurement in case resize observer is slow
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            setScale({
                x: rect.width / NATIVE_WIDTH,
                y: rect.height / NATIVE_HEIGHT
            });
        }

        return () => observer.disconnect();
    }, []);

    const getGraceCountdown = (seat) => {
        if (!seat.vacancy_timer_start || seat.status !== 'Occupied') return null;
        const elapsed = (new Date() - new Date(seat.vacancy_timer_start)) / 60000;
        const remaining = Math.max(0, gracePeriodMinutes - elapsed);
        return remaining > 0 ? `-${remaining.toFixed(0)}m` : null;
    };

    const getConfirmationProgress = (seat) => {
        if (seat.status !== 'Empty' || seat.overlap_percentage < overlapThreshold) return null;
        return `${(seat.overlap_percentage * 100).toFixed(0)}%`;
    };

    const getSeatClasses = (seat) => {
        const classes = ['overlay-seat'];
        if (seat.is_actionable) classes.push('actionable');
        else if (seat.status === 'Occupied') classes.push('occupied');
        else {
            const isDetecting = seat.overlap_percentage >= overlapThreshold;
            if (isDetecting) classes.push('detecting');
            else classes.push('empty');
        }
        return classes.join(' ');
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
            parts.push('(! Click for AI suggestions !)');
        }
        return parts.join('\\n'); // escaped newline for CSS attr()
    };

    return (
        <div className="camera-overlay-container">
            {streamError ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#fff' }}>
                    <p>Live feed unavailable.</p>
                    <button
                        onClick={() => {
                            setStreamError(false);
                            setRetryCount(prev => prev + 1);
                        }}
                        style={{
                            marginTop: '10px', padding: '8px 16px', backgroundColor: '#4caf50',
                            color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'
                        }}
                    >
                        Retry Connection
                    </button>
                </div>
            ) : (
                <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
                    <img
                        key={retryCount}
                        src={`/api/camera-stream?t=${Date.now()}`}
                        alt="Live webcam feed with seat overlay"
                        className="camera-overlay-image"
                        onError={() => setStreamError(true)}
                        onLoad={() => setStreamError(false)}
                    />

                    {/* Render seats overlay */}
                    {seats.map(seat => {
                        const isHovered = hoveredSeat === seat.id;
                        const countdown = getGraceCountdown(seat);
                        const confirmProg = getConfirmationProgress(seat);

                        // Translate absolute coordinates to scaled coordinates
                        const style = {
                            left: `${seat.x * scale.x}px`,
                            top: `${seat.y * scale.y}px`,
                            width: `${seat.width * scale.x}px`,
                            height: `${seat.height * scale.y}px`
                        };

                        return (
                            <div
                                key={seat.id}
                                className={getSeatClasses(seat)}
                                style={style}
                                data-tooltip={formatTooltip(seat)}
                                onMouseEnter={() => setHoveredSeat(seat.id)}
                                onMouseLeave={() => setHoveredSeat(null)}
                                onClick={() => seat.is_actionable && onSeatClick && onSeatClick(seat)}
                            >
                                {/* Small inner indicator for ID or countdown */}
                                <div className="overlay-seat-indicator">
                                    {countdown ? countdown : seat.id}
                                </div>

                                {/* Optional confirmation progress hint */}
                                {confirmProg && !countdown && (
                                    <div style={{
                                        position: 'absolute', bottom: '2px', fontSize: '9px',
                                        color: '#ffeb3b', opacity: 0.95, fontWeight: 'bold',
                                        textShadow: '1px 1px 1px rgba(0,0,0,0.8)'
                                    }}>
                                        {confirmProg}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default CameraOverlay;
