import React, { useState, useEffect, useRef } from 'react';
import SeatGrid from './SeatGrid';
import CameraOverlay from './CameraOverlay';
import { getSeats, getZones, getSuggestions, getConfig, updateConfig, getAnalyticsInsights } from './api';
import './Dashboard.css';

const Dashboard = () => {
  const [seats, setSeats] = useState([]);
  const [zones, setZones] = useState([]);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [streamError, setStreamError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [testingMode, setTestingMode] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);
  const [config, setConfig] = useState(null);
  const [viewMode, setViewMode] = useState('camera'); // 'camera' or 'grid'
  const [isEditingLayout, setIsEditingLayout] = useState(false);
  const [editedSeats, setEditedSeats] = useState([]);
  const [isAutoDetecting, setIsAutoDetecting] = useState(false);
  const fileInputRef = useRef(null); // legacy, only used by OpenCV/auto-calibrate
  const geminiFileInputRef = useRef(null); // Gemini: upload image for AI seat detection
  const bgFileInputRef = useRef(null);      // Upload: set a reference background image

  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(null);
  const [backgroundImageUrl, setBackgroundImageUrl] = useState(null); // reference bg image in edit mode

  // WebSocket state
  const [wsStatus, setWsStatus] = useState('connecting'); // 'live' | 'connecting' | 'error'
  const wsRef = useRef(null);
  const wsReconnectTimer = useRef(null);


  // Load initial config to sync testing mode toggle
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
        setTestingMode(cfg.testing_mode || false);
        setConfigLoaded(true);
      } catch (err) {
        console.error('Error loading config:', err);
      }
    };
    loadConfig();
  }, []);

  // Fetch zones only (seats come via WebSocket)
  const fetchZones = async () => {
    try {
      const zonesData = await getZones();
      setZones(Array.isArray(zonesData) ? zonesData : []);
      setError(null);
    } catch (err) {
      console.error('Error fetching zones:', err);
    } finally {
      setLoading(false);
    }
  };

  // Legacy fetchData used by edit-mode save (still fetches both for a one-shot refresh)
  const fetchData = async () => {
    try {
      const [seatsData, zonesData] = await Promise.all([
        getSeats(),
        getZones(),
      ]);
      setSeats(Array.isArray(seatsData) ? seatsData : []);
      setZones(Array.isArray(zonesData) ? zonesData : []);
      setError(null);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to fetch seat data. Make sure the backend is running on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  // --- WebSocket effect: real-time seat updates ---
  useEffect(() => {
    if (isEditingLayout) {
      // Close WS while editing to avoid stale overwrites
      if (wsRef.current) wsRef.current.close();
      return;
    }

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      setWsStatus('connecting');
      const WS_URL = 'ws://localhost:8000/ws/seats';
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) setWsStatus('live');
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'seats_update' && Array.isArray(msg.seats)) {
            setSeats(msg.seats);
            setLoading(false);
          }
        } catch (e) {
          console.warn('WS parse error:', e);
        }
      };

      ws.onerror = () => {
        if (!cancelled) setWsStatus('error');
      };

      ws.onclose = () => {
        if (cancelled) return;
        setWsStatus('connecting');
        // Auto-reconnect after 3 seconds
        wsReconnectTimer.current = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(wsReconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [isEditingLayout]);

  // --- Zone polling effect: 10-second interval (zones are aggregate, less time-critical) ---
  useEffect(() => {
    if (isEditingLayout) return;
    fetchZones(); // initial load
    const interval = setInterval(fetchZones, 10000);
    return () => clearInterval(interval);
  }, [isEditingLayout]);

  const handleEditToggle = () => {
    if (!isEditingLayout) {
      // Enter edit mode: copy current seats to editedSeats
      setEditedSeats(JSON.parse(JSON.stringify(seats)));
    }
    setIsEditingLayout(!isEditingLayout);
  };

  const handleSaveLayout = async () => {
    try {
      setLoading(true);
      const zoneMap = {};
      zones.forEach(z => zoneMap[z.zone_name] = []);

      editedSeats.forEach(seat => {
        if (!zoneMap[seat.zone]) {
          zoneMap[seat.zone] = [];
        }
        zoneMap[seat.zone].push({
          id: seat.id,
          x: Math.round(seat.x),
          y: Math.round(seat.y),
          width: Math.round(seat.width),
          height: Math.round(seat.height)
        });
      });

      const payload = {
        zones: Object.keys(zoneMap).map(zoneName => ({
          name: zoneName,
          seats: zoneMap[zoneName]
        }))
      };

      const response = await fetch('http://localhost:8000/api/seating-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to save layout');

      setIsEditingLayout(false);
      await fetchData(); // Refresh to get backend truth
    } catch (err) {
      console.error(err);
      setError('Failed to save the new layout to the backend.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddSeat = () => {
    const defaultZone = zones.length > 0 ? zones[0].zone_name : "Default";
    const generateId = () => `Seat-${Math.floor(Math.random() * 10000)}`;
    const newSeat = {
      id: generateId(),
      x: 270,
      y: 190,
      width: 100,
      height: 100,
      zone: defaultZone,
      status: "Empty",
      is_actionable: false,
      overlap_percentage: 0.0
    };
    setEditedSeats([...editedSeats, newSeat]);
  };

  const handleAutoDetect = async (strategy = 'auto') => {
    setIsAutoDetecting(true);
    try {
      const response = await fetch(`http://localhost:8000/api/auto-calibrate?strategy=${strategy}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to auto-detect seats');
      }

      const data = await response.json();
      const defaultZone = zones.length > 0 ? zones[0].zone_name : "Default";

      // Assign IDs to new boxes and shape them properly
      const newSeats = data.boxes.map((box, idx) => ({
        id: `Seat-Auto-${idx}-${Math.floor(Math.random() * 1000)}`,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        zone: defaultZone,
        status: "Empty",
        is_actionable: false,
        overlap_percentage: 0.0
      }));

      // Append them so user doesn't lose previously hand-drawn boxes during session
      setEditedSeats(prev => [...prev, ...newSeats]);

    } catch (err) {
      console.error(err);
      setError(`Auto-calibration (${strategy}) failed. Check backend logs.`);
    } finally {
      setIsAutoDetecting(false);
    }
  };

  /**
   * Gemini Button: user picks an image → Gemini detects seats → boxes appended to editedSeats.
   * Boxes returned by backend are in image-native pixels; we scale them to the 640×480
   * camera canvas coordinate space so they land in sensible positions on the map.
   */
  const handleGeminiImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsAutoDetecting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/upload-layout-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Gemini layout analysis failed');
      }

      const data = await response.json();
      const defaultZone = zones.length > 0 ? zones[0].zone_name : 'Default';

      // Scale coordinates from the uploaded image size to the 640×480 canvas
      const scaleX = data.image_width  ? 640 / data.image_width  : 1;
      const scaleY = data.image_height ? 480 / data.image_height : 1;

      const newSeats = data.boxes.map((box, idx) => ({
        id: `Seat-Gemini-${idx}-${Math.floor(Math.random() * 1000)}`,
        x: Math.round(box.x * scaleX),
        y: Math.round(box.y * scaleY),
        width:  Math.round(box.width  * scaleX),
        height: Math.round(box.height * scaleY),
        zone: defaultZone,
        status: 'Empty',
        is_actionable: false,
        overlap_percentage: 0.0,
      }));

      setEditedSeats(prev => [...prev, ...newSeats]);

    } catch (err) {
      console.error(err);
      setError(`Gemini image analysis failed: ${err.message}`);
    } finally {
      setIsAutoDetecting(false);
      if (geminiFileInputRef.current) geminiFileInputRef.current.value = '';
    }
  };

  /**
   * Upload (Background) Button: user picks an image → saved as reference background.
   * No AI detection is run — purely visual reference behind the seat canvas.
   */
  const handleBackgroundUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsAutoDetecting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/upload-background', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Background upload failed');
      }

      // Append cache-busting query to force reload of the same filename
      setBackgroundImageUrl(`http://localhost:8000/static/layout_background.jpg?t=${Date.now()}`);

    } catch (err) {
      console.error(err);
      setError(`Background upload failed: ${err.message}`);
    } finally {
      setIsAutoDetecting(false);
      if (bgFileInputRef.current) bgFileInputRef.current.value = '';
    }
  };


  const handleSeatUpdate = (updatedSeat) => {
    setEditedSeats(prev => prev.map(s => s.id === updatedSeat.id ? updatedSeat : s));
  };

  const handleSeatDelete = (seatId) => {
    setEditedSeats(prev => prev.filter(s => s.id !== seatId));
  };

  const handleSeatClick = async (seat) => {
    if (!seat.is_actionable) return;

    try {
      setLoading(true);
      const suggestionData = await getSuggestions(seat.zone);
      setSuggestions(suggestionData);
    } catch (err) {
      console.error('Error fetching suggestions:', err);
      setError('Failed to fetch suggestions.');
    } finally {
      setLoading(false);
    }
  };

  const handleTestingModeToggle = async () => {
    const newMode = !testingMode;
    try {
      await updateConfig({ testing_mode: newMode });
      setTestingMode(newMode);
    } catch (err) {
      console.error('Error toggling testing mode:', err);
      setError('Failed to toggle testing mode.');
    }
  };

  const closeSuggestions = () => {
    setSuggestions(null);
  };

  const handleGetAnalytics = async () => {
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const data = await getAnalyticsInsights();
      setAnalyticsData(data);
    } catch (err) {
      console.error('Analytics error:', err);
      setAnalyticsError(err.message);
      setAnalyticsData({ insight: null, error: err.message });
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const closeAnalytics = () => {
    setAnalyticsData(null);
    setAnalyticsError(null);
  };

  if (loading && seats.length === 0) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading venue data...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Venue Intelligence AI Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="status-indicator" title={`WebSocket: ${wsStatus}`}>
            <span className="status-dot" style={{
              backgroundColor:
                wsStatus === 'live' ? '#4caf50' :
                wsStatus === 'connecting' ? '#ff9800' : '#f44336'
            }}></span>
            <span style={{ color:
              wsStatus === 'live' ? '#4caf50' :
              wsStatus === 'connecting' ? '#ff9800' : '#f44336'
            }}>
              {wsStatus === 'live' ? 'Live' : wsStatus === 'connecting' ? 'Connecting…' : 'Disconnected'}
            </span>
          </div>
          <button
            onClick={handleGetAnalytics}
            disabled={analyticsLoading}
            style={{
              padding: '6px 14px',
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: analyticsLoading ? 'wait' : 'pointer',
              fontSize: '13px',
              fontWeight: 'bold',
              transition: 'opacity 0.2s',
              opacity: analyticsLoading ? 0.7 : 1,
            }}
            title="Generate a real-time AI trend analysis for this session"
          >
            {analyticsLoading ? '⏳ Analyzing...' : '📊 Live AI Analytics'}
          </button>
          <button
            onClick={handleTestingModeToggle}
            style={{
              padding: '6px 14px',
              backgroundColor: testingMode ? '#ff9800' : '#555',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s'
            }}
            title={testingMode
              ? 'Testing Mode ON — timers bypassed, instant status changes'
              : 'Testing Mode OFF — normal 30s confirmation / 20min grace period'}
          >
            {testingMode ? '⚡ Testing Mode ON' : 'Testing Mode OFF'}
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="dashboard-content">
        <div className="dashboard-sidebar">
          <div className="zones-summary">
            <h2>Zone Statistics</h2>
            {zones.map(zone => (
              <div key={zone.zone_name} className="zone-stat-card">
                <h3>{zone.zone_name}</h3>
                <div className="stat-row">
                  <span>Total Seats:</span>
                  <strong>{zone.total_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Occupied:</span>
                  <strong style={{ color: '#f44336' }}>{zone.occupied_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Unoccupied:</span>
                  <strong style={{ color: '#9e9e9e' }}>{zone.empty_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Empty %:</span>
                  <strong>{(zone.empty_percentage ?? 0).toFixed(1)}%</strong>
                </div>
                <div className="stat-row">
                  <span>Actionable:</span>
                  <strong style={{ color: '#ff9800' }}>{zone.actionable_seats}</strong>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="dashboard-main">

          {/* === Session Analytics Bar === */}
          {zones.length > 0 && (() => {
            const total = zones.reduce((s, z) => s + z.total_seats, 0);
            const occupied = zones.reduce((s, z) => s + z.occupied_seats, 0);
            const actionable = zones.reduce((s, z) => s + z.actionable_seats, 0);
            const empty = total - occupied - actionable;
            const pct = (n) => total > 0 ? ((n / total) * 100).toFixed(1) : 0;
            return (
              <div style={{ marginBottom: '20px' }}>
                <h2 style={{ marginBottom: '8px' }}>Session Overview</h2>
                <div style={{
                  display: 'flex', height: '28px', borderRadius: '6px',
                  overflow: 'hidden', boxShadow: '0 2px 6px rgba(0,0,0,0.15)'
                }}>
                  {occupied > 0 && (
                    <div title={`Occupied: ${occupied} (${pct(occupied)}%)`} style={{
                      width: `${pct(occupied)}%`, backgroundColor: '#f44336',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'white', fontSize: '11px', fontWeight: 'bold', transition: 'width 0.5s'
                    }}>{pct(occupied)}%</div>
                  )}
                  {actionable > 0 && (
                    <div title={`Actionable: ${actionable} (${pct(actionable)}%)`} style={{
                      width: `${pct(actionable)}%`, backgroundColor: '#ff9800',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'white', fontSize: '11px', fontWeight: 'bold', transition: 'width 0.5s'
                    }}>{pct(actionable)}%</div>
                  )}
                  {empty > 0 && (
                    <div title={`Empty: ${empty} (${pct(empty)}%)`} style={{
                      flex: 1, backgroundColor: '#9e9e9e',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'white', fontSize: '11px', fontWeight: 'bold'
                    }}>{pct(empty)}%</div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '12px', color: '#666' }}>
                  <span style={{ color: '#f44336' }}>● Occupied: {occupied}</span>
                  <span style={{ color: '#ff9800' }}>● Actionable: {actionable}</span>
                  <span style={{ color: '#9e9e9e' }}>● Empty: {empty}</span>
                  <span>Total: {total}</span>
                </div>
              </div>
            );
          })()}

          <div className="seat-visualization">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2>Seat Map</h2>
              <div className="view-mode-toggle" style={{ display: 'flex', gap: '8px', backgroundColor: '#eee', padding: '4px', borderRadius: '6px' }}>
                <button
                  onClick={() => setViewMode('camera')}
                  style={{
                    padding: '6px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer',
                    backgroundColor: viewMode === 'camera' ? '#2196f3' : 'transparent',
                    color: viewMode === 'camera' ? 'white' : '#555',
                    fontWeight: viewMode === 'camera' ? 'bold' : 'normal',
                    transition: 'all 0.2s'
                  }}>
                  Live Camera
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  style={{
                    padding: '6px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer',
                    backgroundColor: viewMode === 'grid' ? '#2196f3' : 'transparent',
                    color: viewMode === 'grid' ? 'white' : '#555',
                    fontWeight: viewMode === 'grid' ? 'bold' : 'normal',
                    transition: 'all 0.2s'
                  }}>
                  Abstract Grid
                </button>
                <div style={{ width: '1px', backgroundColor: '#ccc', margin: '0 4px' }}></div>
                {isEditingLayout && (
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                      title="Upload a photo of your venue — Gemini AI will detect and generate seat boxes from the image"
                      onClick={() => geminiFileInputRef.current?.click()}
                      disabled={isAutoDetecting}
                      style={{
                        padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: isAutoDetecting ? 'wait' : 'pointer',
                        backgroundColor: '#673ab7', color: 'white', fontWeight: 'bold', transition: 'all 0.2s', opacity: isAutoDetecting ? 0.7 : 1
                      }}>
                      📷 Gemini
                    </button>
                    <button
                      title="Use fast local math to analyze the live camera"
                      onClick={() => handleAutoDetect('opencv')}
                      disabled={isAutoDetecting}
                      style={{
                        padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: isAutoDetecting ? 'wait' : 'pointer',
                        backgroundColor: '#0288d1', color: 'white', fontWeight: 'bold', transition: 'all 0.2s', opacity: isAutoDetecting ? 0.7 : 1
                      }}>
                      📐 OpenCV
                    </button>
                    <button
                      title="Upload a reference background image (no AI detection — for manual seat placement)"
                      onClick={() => bgFileInputRef.current?.click()}
                      disabled={isAutoDetecting}
                      style={{
                        padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: isAutoDetecting ? 'wait' : 'pointer',
                        backgroundColor: '#e91e63', color: 'white', fontWeight: 'bold', transition: 'all 0.2s', opacity: isAutoDetecting ? 0.7 : 1
                      }}>
                      🖼️ Upload
                    </button>
                    {/* Hidden: Gemini image input (for AI seat detection from a photo) */}
                    <input
                      type="file"
                      ref={geminiFileInputRef}
                      style={{ display: 'none' }}
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handleGeminiImageUpload}
                    />
                    {/* Hidden: background reference image input */}
                    <input
                      type="file"
                      ref={bgFileInputRef}
                      style={{ display: 'none' }}
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handleBackgroundUpload}
                    />
                  </div>
                )}
                {isEditingLayout && (
                  <button
                    onClick={handleAddSeat}
                    style={{
                      padding: '6px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer',
                      backgroundColor: '#4caf50',
                      color: 'white',
                      fontWeight: 'bold',
                      transition: 'all 0.2s'
                    }}>
                    + Add Seat
                  </button>
                )}
                <button
                  onClick={isEditingLayout ? handleSaveLayout : handleEditToggle}
                  style={{
                    padding: '6px 16px', border: '1px solid #2196f3', borderRadius: '4px', cursor: 'pointer',
                    backgroundColor: isEditingLayout ? '#e3f2fd' : 'transparent',
                    color: '#2196f3',
                    fontWeight: 'bold',
                    transition: 'all 0.2s'
                  }}>
                  {isEditingLayout ? 'Save Layout' : 'Edit Layout'}
                </button>
                {isEditingLayout && (
                  <button
                    onClick={() => setIsEditingLayout(false)}
                    style={{
                      padding: '6px 16px', border: '1px solid #f44336', borderRadius: '4px', cursor: 'pointer',
                      backgroundColor: 'transparent',
                      color: '#f44336',
                      fontWeight: 'bold',
                      transition: 'all 0.2s'
                    }}>
                    Cancel
                  </button>
                )}
              </div>
            </div>
            <div className="legend">
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#9e9e9e' }}></div>
                <span>Unoccupied</span>
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#f44336' }}></div>
                <span>Occupied</span>
              </div>
              <div className="legend-item">
                <div className="legend-color" style={{ backgroundColor: '#ff9800' }}></div>
                <span>Actionable (Click for suggestions)</span>
              </div>
            </div>

            {viewMode === 'camera' ? (
              <CameraOverlay
                seats={isEditingLayout ? editedSeats : seats}
                onSeatClick={handleSeatClick}
                config={config}
                isEditingLayout={isEditingLayout}
                onSeatUpdate={handleSeatUpdate}
                onSeatDelete={handleSeatDelete}
                backgroundImageUrl={backgroundImageUrl}
              />
            ) : (
              <SeatGrid
                seats={isEditingLayout ? editedSeats : seats}
                onSeatClick={handleSeatClick}
                config={config}
                isEditingLayout={isEditingLayout}
                onSeatUpdate={handleSeatUpdate}
                onSeatDelete={handleSeatDelete}
              />
            )}
          </div>
        </div>
      </div>

      {suggestions && (
        <div className="suggestions-modal" onClick={closeSuggestions}>
          <div className="suggestions-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-button" onClick={closeSuggestions}>x</button>
            <h2>AI Suggestions for {suggestions.zone_name}</h2>
            <div className="suggestion-stats">
              <p>
                {suggestions.empty_percentage.toFixed(1)}% unoccupied for{' '}
                {suggestions.empty_duration_minutes.toFixed(1)} minutes
              </p>
            </div>
            <ul className="suggestions-list">
              {suggestions.suggestions.map((suggestion, index) => {
                const energyMatch = suggestion.match(/^\[Energy\]/i);
                const venueMatch = suggestion.match(/^\[Venue\]/i);
                const text = suggestion.replace(/^\[(Energy|Venue)\]\s*/i, '');
                return (
                  <li key={index}>
                    {energyMatch && (
                      <span style={{
                        display: 'inline-block', marginRight: '8px', padding: '2px 8px',
                        backgroundColor: '#e8f5e9', color: '#2e7d32', borderRadius: '10px',
                        fontSize: '11px', fontWeight: 'bold', verticalAlign: 'middle'
                      }}>⚡ Energy</span>
                    )}
                    {venueMatch && (
                      <span style={{
                        display: 'inline-block', marginRight: '8px', padding: '2px 8px',
                        backgroundColor: '#e3f2fd', color: '#1565c0', borderRadius: '10px',
                        fontSize: '11px', fontWeight: 'bold', verticalAlign: 'middle'
                      }}>🏛 Venue</span>
                    )}
                    {text}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {/* === AI Analytics Modal === */}
      {analyticsData && (
        <div className="suggestions-modal" onClick={closeAnalytics}>
          <div className="suggestions-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '560px' }}>
            <button className="close-button" onClick={closeAnalytics}>x</button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <span style={{ fontSize: '22px' }}>📊</span>
              <h2 style={{ margin: 0 }}>Live Event Analytics</h2>
            </div>
            {analyticsData.snapshot_count > 0 && (
              <div style={{
                display: 'inline-block', padding: '3px 10px', marginBottom: '14px',
                background: 'linear-gradient(135deg, #667eea22, #764ba222)',
                border: '1px solid #764ba255', borderRadius: '20px',
                fontSize: '12px', color: '#764ba2'
              }}>
                Based on {analyticsData.snapshot_count} snapshot{analyticsData.snapshot_count !== 1 ? 's' : ''} from this session
              </div>
            )}
            {analyticsData.insight ? (
              <div style={{
                background: 'linear-gradient(135deg, #f8f9ff, #f0f0ff)',
                border: '1px solid #ddd8ff',
                borderRadius: '10px',
                padding: '16px 20px',
                fontSize: '15px',
                lineHeight: '1.7',
                color: '#2d2d4e',
                fontStyle: 'normal',
                whiteSpace: 'pre-line'
              }}>
                {analyticsData.insight}
              </div>
            ) : (
              <div style={{ color: '#e53935', padding: '12px' }}>
                ⚠️ {analyticsData.error || 'Could not generate insights.'}
              </div>
            )}
            <div style={{ marginTop: '14px', fontSize: '12px', color: '#999' }}>
              Generated at {analyticsData.generated_at}
              {' '}· Powered by Gemini 1.5 Flash
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
