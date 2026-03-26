import React, { useState, useRef, useEffect } from 'react';
import './CameraOverlay.css';

const NATIVE_WIDTH = 640;
const NATIVE_HEIGHT = 480;

const CameraOverlay = ({ seats = [], onSeatClick, config, isEditingLayout, onSeatUpdate, onSeatDelete, backgroundImageUrl, zones = [], selectedSeatId = null, setSelectedSeatId = null }) => {
    const containerRef = useRef(null);
    const [scale, setScale] = useState({ x: 1, y: 1 });
    const [hoveredSeat, setHoveredSeat] = useState(null);
    const [streamError, setStreamError] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    const [draggingSeat, setDraggingSeat] = useState(null);
    const [resizingSeat, setResizingSeat] = useState(null);

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

    const handlePointerDown = (e, seat, isResize = false) => {
        if (!isEditingLayout) return;
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const startY = e.clientY;

        if (isResize) {
            setResizingSeat({
                id: seat.id,
                startX, startY,
                initialWidth: seat.width,
                initialHeight: seat.height
            });
        } else {
            setDraggingSeat({
                id: seat.id,
                startX, startY,
                initialX: seat.x,
                initialY: seat.y
            });
        }
    };

    const handlePointerMove = (e) => {
        if (!isEditingLayout) return;

        if (draggingSeat) {
            const dx = (e.clientX - draggingSeat.startX) / scale.x;
            const dy = (e.clientY - draggingSeat.startY) / scale.y;
            onSeatUpdate({
                ...seats.find(s => s.id === draggingSeat.id),
                x: draggingSeat.initialX + dx,
                y: draggingSeat.initialY + dy
            });
        } else if (resizingSeat) {
            const dx = (e.clientX - resizingSeat.startX) / scale.x;
            const dy = (e.clientY - resizingSeat.startY) / scale.y;
            onSeatUpdate({
                ...seats.find(s => s.id === resizingSeat.id),
                width: Math.max(20, resizingSeat.initialWidth + dx),
                height: Math.max(20, resizingSeat.initialHeight + dy)
            });
        }
    };

    const handlePointerUp = () => {
        if (draggingSeat) setDraggingSeat(null);
        if (resizingSeat) setResizingSeat(null);
    };

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
                <div
                    ref={containerRef}
                    style={{ position: 'relative', width: '100%', touchAction: isEditingLayout ? 'none' : 'auto', overflow: 'hidden' }}
                    onPointerMove={handlePointerMove}
                    onPointerUp={handlePointerUp}
                    onPointerLeave={handlePointerUp}
                >
                    <img
                        key={retryCount}
                        src={`/api/camera-stream?t=${Date.now()}`}
                        alt="Live webcam feed with seat overlay"
                        className="camera-overlay-image"
                        onError={() => setStreamError(true)}
                        onLoad={() => setStreamError(false)}
                    />

                    {/* Reference background image overlay (shown during editing) */}
                    {isEditingLayout && backgroundImageUrl && (
                        <img
                            src={backgroundImageUrl}
                            alt="Reference layout background"
                            style={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                width: '100%',
                                height: '100%',
                                objectFit: 'cover',
                                opacity: 0.45,
                                pointerEvents: 'none',
                                zIndex: 0,
                            }}
                        />
                    )}
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
                            height: `${seat.height * scale.y}px`,
                            zIndex: (draggingSeat?.id === seat.id || resizingSeat?.id === seat.id) ? 100 : 1,
                            cursor: isEditingLayout ? (draggingSeat?.id === seat.id ? 'grabbing' : 'grab') : (seat.is_actionable ? 'pointer' : 'default'),
                            border: isEditingLayout ? '2px dashed #2196f3' : undefined,
                            boxShadow: isEditingLayout ? '0 0 10px rgba(33, 150, 243, 0.5)' : undefined,
                            backgroundColor: isEditingLayout ? 'rgba(33, 150, 243, 0.2)' : undefined,
                        };

                        return (
                            <div
                                key={seat.id}
                                className={getSeatClasses(seat)}
                                style={style}
                                data-tooltip={isEditingLayout ? 'Drag to move, bottom-right to resize' : formatTooltip(seat)}
                                onMouseEnter={() => setHoveredSeat(seat.id)}
                                onMouseLeave={() => setHoveredSeat(null)}
                                onClick={() => {
                                    if (isEditingLayout) {
                                        if (setSelectedSeatId) setSelectedSeatId(selectedSeatId === seat.id ? null : seat.id);
                                    } else if (seat.is_actionable && onSeatClick) {
                                        onSeatClick(seat);
                                    }
                                }}
                                onPointerDown={(e) => handlePointerDown(e, seat, false)}
                            >
                                {isEditingLayout && (
                                    <>
                                        <div
                                            onClick={(e) => { e.stopPropagation(); onSeatDelete(seat.id); }}
                                            style={{ position: 'absolute', top: -10, right: -10, background: '#f44336', color: 'white', borderRadius: '50%', width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', zIndex: 101, fontSize: '14px', fontWeight: 'bold', boxShadow: '0 2px 4px rgba(0,0,0,0.3)' }}
                                            title="Delete Seat"
                                        >
                                            ×
                                        </div>
                                        <div
                                            onPointerDown={(e) => handlePointerDown(e, seat, true)}
                                            style={{ position: 'absolute', bottom: -6, right: -6, width: 16, height: 16, background: '#2196f3', cursor: 'nwse-resize', borderRadius: '50%', zIndex: 101, boxShadow: '0 2px 4px rgba(0,0,0,0.3)', border: '2px solid white' }}
                                            title="Resize Seat"
                                        />
                                    </>
                                )}

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

                                {/* Floating Seat Editor Panel */}
                                {isEditingLayout && selectedSeatId === seat.id && (
                                    <div
                                        className="seat-editor-panel"
                                        style={{
                                            position: 'absolute',
                                            top: '100%', left: '50%', transform: 'translateX(-50%)',
                                            marginTop: '8px',
                                            background: '#1e293b', border: '1px solid #38bdf8',
                                            borderRadius: '6px', padding: '8px', zIndex: 1000,
                                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)',
                                            display: 'flex', flexDirection: 'column', gap: '8px',
                                            width: '180px', cursor: 'default'
                                        }}
                                        onClick={(e) => e.stopPropagation()}
                                        onPointerDown={(e) => e.stopPropagation()}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 'bold' }}>{seat.id}</span>
                                            <button onClick={() => { if(setSelectedSeatId) setSelectedSeatId(null); }} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '2px' }}>✕</button>
                                        </div>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                            <label style={{ fontSize: '11px', color: '#cbd5e1' }}>Zone</label>
                                            <select
                                                value={seat.zone}
                                                onChange={(e) => onSeatUpdate({ ...seat, zone: e.target.value })}
                                                style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '4px', borderRadius: '4px', fontSize: '12px' }}
                                            >
                                                {zones.map(z => <option key={z.zone_name} value={z.zone_name}>{z.zone_name}</option>)}
                                            </select>
                                        </div>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                                                <label style={{ fontSize: '11px', color: '#cbd5e1' }}>W</label>
                                                <input type="number" value={Math.round(seat.width)} onChange={(e) => onSeatUpdate({ ...seat, width: Math.max(20, parseInt(e.target.value) || 20) })} style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '4px', borderRadius: '4px', fontSize: '12px', width: '100%' }} />
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                                                <label style={{ fontSize: '11px', color: '#cbd5e1' }}>H</label>
                                                <input type="number" value={Math.round(seat.height)} onChange={(e) => onSeatUpdate({ ...seat, height: Math.max(20, parseInt(e.target.value) || 20) })} style={{ background: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '4px', borderRadius: '4px', fontSize: '12px', width: '100%' }} />
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => { onSeatDelete(seat.id); if(setSelectedSeatId) setSelectedSeatId(null); }}
                                            style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer', marginTop: '4px' }}
                                        >
                                            Delete Seat
                                        </button>
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
