import React, { useState, useEffect } from 'react';
import SeatGrid from './SeatGrid';
import { getSeats, getZones, getSuggestions, getConfig, updateConfig } from './api';
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

  // Load initial config to sync testing mode toggle
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const cfg = await getConfig();
        setTestingMode(cfg.testing_mode || false);
        setConfigLoaded(true);
      } catch (err) {
        console.error('Error loading config:', err);
      }
    };
    loadConfig();
  }, []);

  useEffect(() => {
    fetchData();
    // Poll every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

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
          <div className="status-indicator">
            <span className="status-dot"></span>
            <span>Live</span>
          </div>
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

        <div className="live-camera-section">
          <h2>Live camera</h2>
          <div className="camera-stream-wrapper">
            {streamError ? (
              <div className="camera-stream-fallback">
                <p>Live feed unavailable.</p>
                <p>Check that the backend is running and the webcam is connected.</p>
                <button
                  onClick={() => {
                    setStreamError(false);
                    setRetryCount(prev => prev + 1);
                  }}
                  style={{
                    marginTop: '10px',
                    padding: '8px 16px',
                    backgroundColor: '#4caf50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Retry Connection
                </button>
              </div>
            ) : (
              <img
                key={retryCount}
                src={`/api/camera-stream?t=${Date.now()}`}
                alt="Live webcam feed with seat overlay"
                className="camera-stream"
                onError={() => {
                  console.error('Camera stream error');
                  setStreamError(true);
                }}
                onLoad={() => {
                  setStreamError(false);
                }}
              />
            )}
          </div>
        </div>

        <div className="seat-visualization">
          <h2>Seat Map</h2>
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
          <SeatGrid seats={seats} onSeatClick={handleSeatClick} />
        </div>
      </div>

      {suggestions && (
        <div className="suggestions-modal" onClick={closeSuggestions}>
          <div className="suggestions-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-button" onClick={closeSuggestions}>x</button>
            <h2>AI Suggestions for {suggestions.zone_name}</h2>
            <div className="suggestion-stats">
              <p>
                {suggestions.empty_percentage.toFixed(1)}% empty for{' '}
                {suggestions.empty_duration_minutes.toFixed(1)} minutes
              </p>
            </div>
            <ul className="suggestions-list">
              {suggestions.suggestions.map((suggestion, index) => (
                <li key={index}>{suggestion}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
