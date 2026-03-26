import React from 'react';
import Dashboard from './Dashboard';
import Sidebar from './Sidebar';
import './App.css';

function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <Dashboard />
    </div>
  );
}

export default App;
