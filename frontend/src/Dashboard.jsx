import React, { useState, useEffect, useRef } from 'react';
import SeatGrid from './SeatGrid';
import CameraOverlay from './CameraOverlay';
import { getSeats, getZones, getSuggestions, getConfig, updateConfig, getAnalyticsInsights } from './api';
import {
  BarChart3, Zap, Sparkles, ScanLine, ImagePlus, Plus, Save, X, MapPin, ImageOff, ChevronDown, Trash2, Video, VideoOff, Edit2, Check
} from 'lucide-react';
import './Dashboard.css';

const Dashboard = () => {
  const [seats, setSeats] = useState([]);
  const [zones, setZones] = useState([]);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [testingMode, setTestingMode] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);
  const [config, setConfig] = useState(null);
  const [viewMode, setViewMode] = useState('camera'); // 'camera' or 'grid'
  const [isEditingLayout, setIsEditingLayout] = useState(false);
  const [editedSeats, setEditedSeats] = useState([]);
  const [isAutoDetecting, setIsAutoDetecting] = useState(false);
  const geminiFileInputRef = useRef(null);
  const bgFileInputRef = useRef(null);

  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState(null);
  const [backgroundImageUrl, setBackgroundImageUrl] = useState(null);
  const [layoutProfiles, setLayoutProfiles] = useState([]);
  const [showLayoutMenu, setShowLayoutMenu] = useState(false);
  const [rtspStatus, setRtspStatus] = useState({ connected: false, error: null });

  // Inline layout editor states
  const [selectedSeatId, setSelectedSeatId] = useState(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [confirmDeleteProfile, setConfirmDeleteProfile] = useState(null);
  const [renamingProfile, setRenamingProfile] = useState(null); // { name, draft }

  // WebSocket state
  const [wsStatus, setWsStatus] = useState('connecting');
  const wsRef = useRef(null);
  const wsReconnectTimer = useRef(null);

  // Load initial config
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

  // Fetch zones (seats come via WebSocket)
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

  // Legacy fetchData for post-edit refresh
  const fetchData = async () => {
    try {
      const [seatsData, zonesData] = await Promise.all([getSeats(), getZones()]);
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

  // WebSocket real-time seat updates
  useEffect(() => {
    if (isEditingLayout) {
      if (wsRef.current) wsRef.current.close();
      return;
    }

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      setWsStatus('connecting');
      const ws = new WebSocket('ws://localhost:8000/ws/seats');
      wsRef.current = ws;

      ws.onopen = () => { if (!cancelled) setWsStatus('live'); };
      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'seats_update' && Array.isArray(msg.seats)) {
            setSeats(msg.seats);
            setLoading(false);
          }
        } catch (e) { console.warn('WS parse error:', e); }
      };
      ws.onerror = () => { if (!cancelled) setWsStatus('error'); };
      ws.onclose = () => {
        if (cancelled) return;
        setWsStatus('connecting');
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

  // Zone polling
  useEffect(() => {
    if (isEditingLayout) return;
    fetchZones();
    const interval = setInterval(fetchZones, 10000);
    return () => clearInterval(interval);
  }, [isEditingLayout]);

  // RTSP status polling
  useEffect(() => {
    const fetchRtspStatus = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/rtsp-status');
        if (res.ok) {
          const data = await res.json();
          setRtspStatus(data);
        }
      } catch (e) {
        setRtspStatus({ connected: false, error: 'Backend unreachable' });
      }
    };
    fetchRtspStatus();
    const interval = setInterval(fetchRtspStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // ---- Handlers ----
  const handleEditToggle = () => {
    if (!isEditingLayout) {
      setEditedSeats(JSON.parse(JSON.stringify(seats)));
      fetchLayouts();
      checkBackground();
    } else {
      setShowLayoutMenu(false);
    }
    setIsEditingLayout(!isEditingLayout);
  };
  
  const fetchLayouts = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/layouts');
      if (res.ok) {
        const data = await res.json();
        setLayoutProfiles(data.layouts || []);
      }
    } catch (e) {
      console.error('Failed to fetch layouts', e);
    }
  };
  
  const checkBackground = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/background-image', { method: 'HEAD' });
      if (res.ok) {
        setBackgroundImageUrl(`http://localhost:8000/api/background-image?t=${Date.now()}`);
      } else {
        setBackgroundImageUrl(null);
      }
    } catch (e) {
      console.error('No background image');
    }
  };

  const handleSaveLayout = async () => {
    try {
      setLoading(true);
      const zoneMap = {};
      zones.forEach(z => (zoneMap[z.zone_name] = []));
      editedSeats.forEach(seat => {
        if (!zoneMap[seat.zone]) zoneMap[seat.zone] = [];
        zoneMap[seat.zone].push({
          id: seat.id,
          x: Math.round(seat.x), y: Math.round(seat.y),
          width: Math.round(seat.width), height: Math.round(seat.height)
        });
      });

      const payload = {
        zones: Object.keys(zoneMap).map(n => ({ name: n, seats: zoneMap[n] }))
      };

      const response = await fetch('http://localhost:8000/api/seating-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to save layout');
      setIsEditingLayout(false);
      await fetchData();
    } catch (err) {
      console.error(err);
      setError('Failed to save the new layout to the backend.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    const name = window.prompt("Enter a name for this layout profile:");
    if (!name) return;
    
    try {
      setLoading(true);
      const zoneMap = {};
      zones.forEach(z => (zoneMap[z.zone_name] = []));
      editedSeats.forEach(seat => {
        if (!zoneMap[seat.zone]) zoneMap[seat.zone] = [];
        zoneMap[seat.zone].push({
          id: seat.id,
          x: Math.round(seat.x), y: Math.round(seat.y),
          width: Math.round(seat.width), height: Math.round(seat.height)
        });
      });

      const payload = {
        name,
        zones: Object.keys(zoneMap).map(n => ({ name: n, seats: zoneMap[n] }))
      };

      const res = await fetch('http://localhost:8000/api/layouts/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save profile");
      await fetchLayouts();
    } catch (e) {
      console.error(e);
      setError("Failed to save layout profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadProfile = async (name) => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:8000/api/layouts/load/${name}`);
      if (!res.ok) throw new Error("Failed to load profile");
      const data = await res.json();
      
      const newSeats = [];
      data.zones.forEach(zone => {
        zone.seats.forEach(seat => {
          newSeats.push({
            id: seat.id || `Seat-${Math.floor(Math.random() * 10000)}`,
            x: seat.x, y: seat.y, width: seat.width, height: seat.height,
            zone: zone.name, status: 'Empty', is_actionable: false, overlap_percentage: 0.0
          });
        });
      });
      setEditedSeats(newSeats);
      setShowLayoutMenu(false);
    } catch (e) {
      console.error(e);
      setError("Failed to load layout profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleRenameProfile = async (oldName, newName) => {
    if (!newName || newName === oldName) {
      setRenamingProfile(null);
      return;
    }
    try {
      const res = await fetch(`http://localhost:8000/api/layouts/${oldName}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName })
      });
      if (!res.ok) throw new Error("Failed to rename profile");
      setRenamingProfile(null);
      await fetchLayouts();
    } catch (err) {
      console.error(err);
      setError("Failed to rename layout profile.");
    }
  };

  const handleOverwriteProfile = async (name, e) => {
    e.stopPropagation();
    try {
      setLoading(true);
      const zoneMap = {};
      zones.forEach(z => (zoneMap[z.zone_name] = []));
      editedSeats.forEach(seat => {
        if (!zoneMap[seat.zone]) zoneMap[seat.zone] = [];
        zoneMap[seat.zone].push({
          id: seat.id,
          x: Math.round(seat.x), y: Math.round(seat.y),
          width: Math.round(seat.width), height: Math.round(seat.height)
        });
      });

      const payload = {
        name,
        zones: Object.keys(zoneMap).map(n => ({ name: n, seats: zoneMap[n] }))
      };

      const res = await fetch('http://localhost:8000/api/layouts/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to overwrite profile");
      setShowLayoutMenu(false);
      await fetchLayouts();
    } catch (err) {
      console.error(err);
      setError("Failed to overwrite layout profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProfile = async (name) => {
    if (!name) return;
    try {
      const res = await fetch(`http://localhost:8000/api/layouts/${name}`, { method: 'DELETE' });
      if (!res.ok) throw new Error("Failed to delete profile");
      setConfirmDeleteProfile(null);
      await fetchLayouts();
    } catch (err) {
      console.error(err);
      setError("Failed to delete layout profile.");
      setConfirmDeleteProfile(null);
    }
  };

  const handleClearAllSeats = () => {
    setEditedSeats([]);
    setConfirmClear(false);
  };

  const handleAddSeat = () => {
    const defaultZone = zones.length > 0 ? zones[0].zone_name : 'Default';
    setEditedSeats([...editedSeats, {
      id: `Seat-${Math.floor(Math.random() * 10000)}`,
      x: 270, y: 190, width: 100, height: 100,
      zone: defaultZone, status: 'Empty', is_actionable: false, overlap_percentage: 0.0
    }]);
  };

  const handleAutoDetect = async (strategy = 'auto') => {
    setIsAutoDetecting(true);
    try {
      const response = await fetch(`http://localhost:8000/api/auto-calibrate?strategy=${strategy}`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to auto-detect seats');
      const data = await response.json();
      const defaultZone = zones.length > 0 ? zones[0].zone_name : 'Default';
      const newSeats = data.boxes.map((box, idx) => ({
        id: `Seat-Auto-${idx}-${Math.floor(Math.random() * 1000)}`,
        x: box.x, y: box.y, width: box.width, height: box.height,
        zone: defaultZone, status: 'Empty', is_actionable: false, overlap_percentage: 0.0
      }));
      setEditedSeats(prev => [...prev, ...newSeats]);
    } catch (err) {
      console.error(err);
      setError(`Auto-calibration (${strategy}) failed. Check backend logs.`);
    } finally {
      setIsAutoDetecting(false);
    }
  };

  const handleGeminiImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsAutoDetecting(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      // Parallel upload to both layout image and background endpoints
      const [aiRes, bgRes] = await Promise.all([
        fetch('http://localhost:8000/api/upload-layout-image', { method: 'POST', body: formData }),
        fetch('http://localhost:8000/api/upload-background', { method: 'POST', body: formData })
      ]);
      
      if (!aiRes.ok) {
        const err = await aiRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Gemini layout analysis failed');
      }
      
      if (bgRes.ok) {
        setBackgroundImageUrl(`http://localhost:8000/api/background-image?t=${Date.now()}`);
      }
      
      const data = await aiRes.json();
      const defaultZone = zones.length > 0 ? zones[0].zone_name : 'Default';
      const scaleX = data.image_width  ? 640 / data.image_width  : 1;
      const scaleY = data.image_height ? 480 / data.image_height : 1;
      const newSeats = data.boxes.map((box, idx) => ({
        id: `Seat-Gemini-${idx}-${Math.floor(Math.random() * 1000)}`,
        x: Math.round(box.x * scaleX), y: Math.round(box.y * scaleY),
        width: Math.round(box.width * scaleX), height: Math.round(box.height * scaleY),
        zone: defaultZone, status: 'Empty', is_actionable: false, overlap_percentage: 0.0
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

  const handleBackgroundUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsAutoDetecting(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch('http://localhost:8000/api/upload-background', { method: 'POST', body: formData });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Background upload failed');
      }
      setBackgroundImageUrl(`http://localhost:8000/api/background-image?t=${Date.now()}`);
    } catch (err) {
      console.error(err);
      setError(`Background upload failed: ${err.message}`);
    } finally {
      setIsAutoDetecting(false);
      if (bgFileInputRef.current) bgFileInputRef.current.value = '';
    }
  };

  const handleRemoveBackground = async () => {
    try {
      await fetch('http://localhost:8000/api/background', { method: 'DELETE' });
      setBackgroundImageUrl(null);
    } catch (e) {
      console.error('Failed to remote background image', e);
    }
  };

  const handleSeatUpdate = (updatedSeat) => {
    setEditedSeats(prev => prev.map(s => s.id === updatedSeat.id ? updatedSeat : s));
  };

  const handleSeatDelete = (seatId) => {
    setEditedSeats(prev => prev.filter(s => s.id !== seatId));
  };

  const handleSeatClick = async (seat) => {
    if (isEditingLayout) {
      // In edit mode, clicking a seat opens the editor panel
      setSelectedSeatId(seat.id === selectedSeatId ? null : seat.id);
      return;
    }
    
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

  // ---- Derived State ----
  const sessionTotal      = zones.reduce((s, z) => s + z.total_seats, 0);
  const sessionOccupied   = zones.reduce((s, z) => s + z.occupied_seats, 0);
  const sessionActionable = zones.reduce((s, z) => s + z.actionable_seats, 0);
  const sessionEmpty      = sessionTotal - sessionOccupied - sessionActionable;
  const pct = (n) => sessionTotal > 0 ? ((n / sessionTotal) * 100).toFixed(1) : '0';

  const wsStatusDotClass = {
    live: 'ws-status-dot--live',
    connecting: 'ws-status-dot--connecting',
    error: 'ws-status-dot--error',
  }[wsStatus] || 'ws-status-dot--connecting';

  const wsStatusLabel = {
    live: 'Live',
    connecting: 'Connecting…',
    error: 'Disconnected',
  }[wsStatus] || 'Connecting…';

  if (loading && seats.length === 0) {
    return (
      <div className="dashboard-loading">
        <div className="spinner" />
        <p>Loading venue data…</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* ---- Header ---- */}
      <header className="dashboard-header">
        <h1>CrowdView AI</h1>

        <div className="dashboard-header-actions">
          {/* WS Status */}
          <div
            className="ws-status"
            aria-live="polite"
            aria-label={`Connection status: ${wsStatusLabel}`}
            title={`WebSocket: ${wsStatus}`}
          >
            <span className={`ws-status-dot ${wsStatusDotClass}`} />
            <span>{wsStatusLabel}</span>
          </div>

          {/* RTSP Status */}
          <div
            className="ws-status"
            aria-live="polite"
            title={`Camera: ${rtspStatus.connected ? 'Connected' : rtspStatus.error || 'Disconnected'}`}
            style={{ 
              color: rtspStatus.connected ? '#4ade80' : '#ef4444', 
              borderColor: rtspStatus.connected ? 'rgba(74, 222, 128, 0.2)' : 'rgba(239, 68, 68, 0.2)',
              backgroundColor: rtspStatus.connected ? 'rgba(74, 222, 128, 0.05)' : 'rgba(239, 68, 68, 0.05)'
            }}
          >
            {rtspStatus.connected ? <Video size={14} /> : <VideoOff size={14} />}
            <span>{rtspStatus.connected ? 'Cam Live' : 'Cam Offline'}</span>
          </div>

          {/* Analytics Button */}
          <button
            className="header-btn header-btn--analytics"
            onClick={handleGetAnalytics}
            disabled={analyticsLoading}
            aria-label="Generate live AI analytics"
            title="Generate a real-time AI trend analysis for this session"
          >
            <BarChart3 size={15} />
            {analyticsLoading ? 'Analyzing…' : 'Live Analytics'}
          </button>

          {/* Testing Mode Toggle */}
          <button
            className={`header-btn ${testingMode ? 'header-btn--testing-on' : 'header-btn--testing-off'}`}
            onClick={handleTestingModeToggle}
            aria-pressed={testingMode}
            title={testingMode
              ? 'Testing Mode ON — timers bypassed, instant status changes'
              : 'Testing Mode OFF — normal 30s confirmation / 20min grace period'}
          >
            <Zap size={15} />
            {testingMode ? 'Testing: ON' : 'Testing: OFF'}
          </button>
        </div>
      </header>

      {/* ---- Error Banner ---- */}
      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button
            className="error-banner__dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss error"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* ---- Main Content ---- */}
      <div className="dashboard-content">

        {/* ---- Sidebar: Zone Stats ---- */}
        <aside className="dashboard-sidebar">
          <div className="zones-summary">
            <h2>Zone Statistics</h2>
            {zones.map(zone => (
              <div key={zone.zone_name} className="zone-stat-card">
                <div className="zone-stat-card__title">
                  <MapPin size={14} />
                  {zone.zone_name}
                </div>
                <div className="stat-row">
                  <span>Total Seats</span>
                  <strong>{zone.total_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Occupied</span>
                  <strong style={{ color: 'var(--color-occupied)' }}>{zone.occupied_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Empty</span>
                  <strong style={{ color: 'var(--color-empty)' }}>{zone.empty_seats}</strong>
                </div>
                <div className="stat-row">
                  <span>Empty %</span>
                  <strong>{(zone.empty_percentage ?? 0).toFixed(1)}%</strong>
                </div>
                <div className="stat-row">
                  <span>Actionable</span>
                  <strong style={{ color: 'var(--color-actionable)' }}>{zone.actionable_seats}</strong>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* ---- Main Panel ---- */}
        <main className="dashboard-main">

          {/* Session Overview Bar */}
          {sessionTotal > 0 && (
            <div className="session-overview">
              <div className="session-overview__title">Session Overview</div>
              <div
                className="session-bar"
                role="meter"
                aria-label={`Seat occupancy: ${pct(sessionOccupied)}% occupied`}
              >
                {sessionOccupied > 0 && (
                  <div
                    className="session-bar__segment session-bar__segment--occupied"
                    style={{ width: `${pct(sessionOccupied)}%` }}
                    title={`Occupied: ${sessionOccupied} (${pct(sessionOccupied)}%)`}
                  >
                    {Number(pct(sessionOccupied)) > 5 && `${pct(sessionOccupied)}%`}
                  </div>
                )}
                {sessionActionable > 0 && (
                  <div
                    className="session-bar__segment session-bar__segment--actionable"
                    style={{ width: `${pct(sessionActionable)}%` }}
                    title={`Actionable: ${sessionActionable} (${pct(sessionActionable)}%)`}
                  >
                    {Number(pct(sessionActionable)) > 5 && `${pct(sessionActionable)}%`}
                  </div>
                )}
                {sessionEmpty > 0 && (
                  <div
                    className="session-bar__segment session-bar__segment--empty"
                    style={{ flex: 1 }}
                    title={`Empty: ${sessionEmpty} (${pct(sessionEmpty)}%)`}
                  >
                    {Number(pct(sessionEmpty)) > 5 && `${pct(sessionEmpty)}%`}
                  </div>
                )}
              </div>
              <div className="session-bar-legend">
                <div className="session-bar-legend__item">
                  <div className="session-bar-legend__dot" style={{ background: 'var(--color-occupied)' }} />
                  <span style={{ color: 'var(--color-occupied)' }}>Occupied: {sessionOccupied}</span>
                </div>
                <div className="session-bar-legend__item">
                  <div className="session-bar-legend__dot" style={{ background: 'var(--color-actionable)' }} />
                  <span style={{ color: 'var(--color-actionable)' }}>Actionable: {sessionActionable}</span>
                </div>
                <div className="session-bar-legend__item">
                  <div className="session-bar-legend__dot" style={{ background: 'var(--color-empty)' }} />
                  <span style={{ color: 'var(--color-secondary, #64748B)' }}>Empty: {sessionEmpty}</span>
                </div>
                <div className="session-bar-legend__item">
                  <span style={{ color: 'var(--text-secondary)' }}>Total: {sessionTotal}</span>
                </div>
              </div>
            </div>
          )}

          {/* Seat Visualization Panel */}
          <div className="seat-visualization">
            <div className="seat-visualization__header">
              <h2>Seat Map</h2>

              {/* Controls Row */}
              <div className="edit-toolbar">
                {/* View Mode Toggle */}
                <div className="view-toggle" role="group" aria-label="View mode">
                  <button
                    className={`view-toggle__btn ${viewMode === 'camera' ? 'view-toggle__btn--active' : 'view-toggle__btn--inactive'}`}
                    onClick={() => setViewMode('camera')}
                    aria-pressed={viewMode === 'camera'}
                  >
                    Live Camera
                  </button>
                  <button
                    className={`view-toggle__btn ${viewMode === 'grid' ? 'view-toggle__btn--active' : 'view-toggle__btn--inactive'}`}
                    onClick={() => setViewMode('grid')}
                    aria-pressed={viewMode === 'grid'}
                  >
                    Abstract Grid
                  </button>
                </div>

                <div className="edit-toolbar__divider" />

                {/* Edit-mode tools */}
                {isEditingLayout && (
                  <>
                    <button
                      className="edit-btn edit-btn--gemini"
                      title="Upload a photo — Gemini AI will detect seat positions from the image"
                      onClick={() => geminiFileInputRef.current?.click()}
                      disabled={isAutoDetecting}
                      aria-label="Detect seats with Gemini AI from image"
                    >
                      <Sparkles size={13} />
                      Gemini
                    </button>
                    <button
                      className="edit-btn edit-btn--opencv"
                      title="Use fast local computer vision to detect seats from the live camera"
                      onClick={() => handleAutoDetect('opencv')}
                      disabled={isAutoDetecting}
                      aria-label="Auto-detect seats with OpenCV"
                    >
                      <ScanLine size={13} />
                      OpenCV
                    </button>
                    <button
                      className="edit-btn edit-btn--upload"
                      title="Upload a reference background image for manual seat placement"
                      onClick={() => bgFileInputRef.current?.click()}
                      disabled={isAutoDetecting}
                      aria-label="Upload background reference image"
                    >
                      <ImagePlus size={13} />
                      Upload BG
                    </button>
                    {backgroundImageUrl && (
                      <button
                        className="edit-btn edit-btn--upload"
                        title="Remove the reference background image"
                        onClick={handleRemoveBackground}
                        disabled={isAutoDetecting}
                        aria-label="Remove background reference image"
                        style={{ color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)' }}
                      >
                        <ImageOff size={13} />
                        Remove BG
                      </button>
                    )}

                    <div className="edit-toolbar__divider" />

                    <button
                      className="edit-btn edit-btn--add"
                      onClick={handleAddSeat}
                      aria-label="Add a new seat"
                    >
                      <Plus size={13} />
                      Add Seat
                    </button>
                    {!confirmClear ? (
                      <button
                        className="edit-btn"
                        style={{ color: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                        onClick={() => setConfirmClear(true)}
                        aria-label="Clear all seats"
                      >
                        <Trash2 size={13} />
                        Clear All
                      </button>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(239, 68, 68, 0.2)', padding: '0 8px', borderRadius: '4px', gap: '4px', height: '32px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                        <span style={{ color: '#fca5a5', fontSize: '13px', marginRight: '4px' }}>Clear all {editedSeats.length}?</span>
                        <button onClick={handleClearAllSeats} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }} title="Confirm"><Check size={14} /></button>
                        <button onClick={() => setConfirmClear(false)} style={{ background: 'none', border: 'none', color: '#f8fafc', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }} title="Cancel"><X size={14} /></button>
                      </div>
                    )}
                  </>
                )}

                {/* Save / Edit Layout */}
                {isEditingLayout ? (
                  <>
                    <div style={{ position: 'relative' }}>
                      <button
                        className="edit-btn edit-btn--layout"
                        onClick={() => setShowLayoutMenu(!showLayoutMenu)}
                        aria-label="Layout Profiles"
                        style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                      >
                        Profiles <ChevronDown size={13} />
                      </button>
                      {showLayoutMenu && (
                        <div style={{
                          position: 'absolute', top: '100%', right: 0, marginTop: '4px',
                          background: '#1e293b', border: '1px solid #334155', borderRadius: '4px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.5)', zIndex: 1000,
                          minWidth: '200px', display: 'flex', flexDirection: 'column',
                          padding: '4px'
                        }}>
                          <button 
                            style={{ background: 'none', border: 'none', color: '#38bdf8', padding: '8px 12px', textAlign: 'left', cursor: 'pointer', borderRadius: '2px', display: 'flex', gap: '8px', alignItems: 'center' }}
                            onClick={handleSaveProfile}
                            onMouseOver={(e) => e.currentTarget.style.background = '#334155'}
                            onMouseOut={(e) => e.currentTarget.style.background = 'none'}
                          >
                            <Save size={14} /> Save Current as Profile
                          </button>
                          
                          {layoutProfiles.length > 0 && <div style={{ height: '1px', background: '#334155', margin: '4px 0' }} />}
                          
                          {layoutProfiles.map(profile => (
                            <div key={profile} style={{ display: 'flex', alignItems: 'center', padding: '4px 4px 4px 12px', borderRadius: '2px', minHeight: '32px' }}
                              onMouseOver={(e) => { if (!confirmDeleteProfile && (!renamingProfile || renamingProfile.name !== profile)) e.currentTarget.style.background = '#334155'; }}
                              onMouseOut={(e) => { if (!confirmDeleteProfile && (!renamingProfile || renamingProfile.name !== profile)) e.currentTarget.style.background = 'none'; }}
                            >
                              {confirmDeleteProfile === profile ? (
                                <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '8px' }}>
                                  <span style={{ flex: 1, color: '#f8fafc', fontSize: '13px' }}>Delete {profile}?</span>
                                  <button onClick={(e) => { e.stopPropagation(); handleDeleteProfile(profile); }} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px' }} title="Confirm Delete"><Check size={14} /></button>
                                  <button onClick={(e) => { e.stopPropagation(); setConfirmDeleteProfile(null); }} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }} title="Cancel"><X size={14} /></button>
                                </div>
                              ) : renamingProfile?.name === profile ? (
                                <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '4px' }}>
                                  <input
                                    type="text"
                                    value={renamingProfile.draft}
                                    onChange={(e) => setRenamingProfile({ ...renamingProfile, draft: e.target.value })}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') handleRenameProfile(profile, renamingProfile.draft);
                                      if (e.key === 'Escape') setRenamingProfile(null);
                                    }}
                                    onBlur={() => handleRenameProfile(profile, renamingProfile.draft)}
                                    autoFocus
                                    style={{ flex: 1, background: '#0f172a', border: '1px solid #38bdf8', color: '#f8fafc', padding: '2px 6px', borderRadius: '2px', fontSize: '13px', outline: 'none', width: '100%' }}
                                  />
                                </div>
                              ) : (
                                <>
                                  <span 
                                    style={{ flex: 1, color: '#f8fafc', cursor: 'pointer', fontSize: '13px' }}
                                    onClick={() => handleLoadProfile(profile)}
                                    onDoubleClick={() => setRenamingProfile({ name: profile, draft: profile })}
                                    title="Double-click to rename"
                                  >
                                    Load: {profile}
                                  </span>
                                  <button
                                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                                    onClick={(e) => { e.stopPropagation(); setRenamingProfile({ name: profile, draft: profile }); }}
                                    title="Rename Profile"
                                    onMouseOver={(e) => e.currentTarget.style.color = '#38bdf8'}
                                    onMouseOut={(e) => e.currentTarget.style.color = '#94a3b8'}
                                  >
                                    <Edit2 size={13} />
                                  </button>
                                  <button
                                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                                    onClick={(e) => handleOverwriteProfile(profile, e)}
                                    title="Overwrite Profile with Current Layout"
                                    onMouseOver={(e) => e.currentTarget.style.color = '#10b981'}
                                    onMouseOut={(e) => e.currentTarget.style.color = '#94a3b8'}
                                  >
                                    <Save size={13} />
                                  </button>
                                  <button
                                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px' }}
                                    onClick={(e) => { e.stopPropagation(); setConfirmDeleteProfile(profile); }}
                                    onMouseOver={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'}
                                    onMouseOut={(e) => e.currentTarget.style.background = 'none'}
                                    title="Delete Profile"
                                  >
                                    <Trash2 size={13} />
                                  </button>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <button
                      className="edit-btn edit-btn--save"
                      onClick={handleSaveLayout}
                      aria-label="Save layout changes to map"
                    >
                      <Save size={13} />
                      Publish
                    </button>
                    <button
                      className="edit-btn edit-btn--cancel"
                      onClick={() => setIsEditingLayout(false)}
                      aria-label="Cancel layout editing"
                    >
                      <X size={13} />
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="edit-btn edit-btn--layout"
                    onClick={handleEditToggle}
                    aria-label="Enter layout editing mode"
                  >
                    Edit Layout
                  </button>
                )}
              </div>
            </div>

            {/* Hidden file inputs */}
            <input type="file" ref={geminiFileInputRef} style={{ display: 'none' }}
              accept="image/jpeg,image/png,image/webp" onChange={handleGeminiImageUpload} />
            <input type="file" ref={bgFileInputRef} style={{ display: 'none' }}
              accept="image/jpeg,image/png,image/webp" onChange={handleBackgroundUpload} />

            {/* Legend */}
            <div className="legend" role="list" aria-label="Seat status legend">
              <div className="legend-item" role="listitem">
                <div className="legend-color" style={{ backgroundColor: 'var(--color-empty)' }} aria-hidden="true" />
                <span>Empty</span>
              </div>
              <div className="legend-item" role="listitem">
                <div className="legend-color" style={{ backgroundColor: 'var(--color-occupied)' }} aria-hidden="true" />
                <span>Occupied</span>
              </div>
              <div className="legend-item" role="listitem">
                <div className="legend-color" style={{ backgroundColor: 'var(--color-actionable)' }} aria-hidden="true" />
                <span>Actionable — click for AI suggestions</span>
              </div>
            </div>

            {/* View */}
            {viewMode === 'camera' ? (
              <CameraOverlay
                seats={isEditingLayout ? editedSeats : seats}
                onSeatClick={handleSeatClick}
                config={config}
                isEditingLayout={isEditingLayout}
                onSeatUpdate={handleSeatUpdate}
                onSeatDelete={handleSeatDelete}
                backgroundImageUrl={backgroundImageUrl}
                zones={zones}
                selectedSeatId={selectedSeatId}
                setSelectedSeatId={setSelectedSeatId}
              />
            ) : (
              <SeatGrid
                seats={isEditingLayout ? editedSeats : seats}
                onSeatClick={handleSeatClick}
                config={config}
                isEditingLayout={isEditingLayout}
                onSeatUpdate={handleSeatUpdate}
                onSeatDelete={handleSeatDelete}
                zones={zones}
                selectedSeatId={selectedSeatId}
                setSelectedSeatId={setSelectedSeatId}
              />
            )}
          </div>
        </main>
      </div>

      {/* ---- Suggestions Modal ---- */}
      {suggestions && (
        <div className="modal-overlay" onClick={() => setSuggestions(null)} role="dialog" aria-modal="true" aria-label="AI suggestions">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>AI Suggestions — {suggestions.zone_name}</h2>
              <button className="modal-close" onClick={() => setSuggestions(null)} aria-label="Close suggestions">
                <X size={20} />
              </button>
            </div>
            <div className="suggestion-stats">
              {suggestions.empty_percentage.toFixed(1)}% empty for {suggestions.empty_duration_minutes.toFixed(1)} minutes
            </div>
            <ul className="suggestions-list">
              {suggestions.suggestions.map((suggestion, index) => {
                const energyMatch = suggestion.match(/^\[Energy\]/i);
                const venueMatch = suggestion.match(/^\[Venue\]/i);
                const text = suggestion.replace(/^\[(Energy|Venue)\]\s*/i, '');
                return (
                  <li key={index}>
                    {energyMatch && <span className="suggestion-tag suggestion-tag--energy">Energy</span>}
                    {venueMatch && <span className="suggestion-tag suggestion-tag--venue">Venue</span>}
                    {text}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {/* ---- Analytics Modal ---- */}
      {analyticsData && (
        <div className="modal-overlay" onClick={() => { setAnalyticsData(null); setAnalyticsError(null); }} role="dialog" aria-modal="true" aria-label="Live event analytics">
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <BarChart3 size={20} style={{ color: 'var(--color-primary)', flexShrink: 0 }} aria-hidden="true" />
              <h2>Live Event Analytics</h2>
              <button className="modal-close" onClick={() => { setAnalyticsData(null); setAnalyticsError(null); }} aria-label="Close analytics">
                <X size={20} />
              </button>
            </div>

            {analyticsData.snapshot_count > 0 && (
              <div className="analytics-badge">
                Based on {analyticsData.snapshot_count} snapshot{analyticsData.snapshot_count !== 1 ? 's' : ''} this session
              </div>
            )}

            {analyticsData.insight ? (
              <div className="analytics-insight">{analyticsData.insight}</div>
            ) : (
              <div className="analytics-error">
                {analyticsData.error || 'Could not generate insights.'}
              </div>
            )}

            <div className="analytics-footer">
              Generated at {analyticsData.generated_at} · Powered by Gemini 1.5 Flash
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
