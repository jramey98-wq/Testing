import { useState, useEffect } from 'react';
import LiveScores from './components/LiveScores';
import Bracket from './components/Bracket';
import './App.css';

type Tab = 'scores' | 'bracket';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('scores');
  const [clock, setClock] = useState('');

  useEffect(() => {
    const tick = () => {
      setClock(
        new Date().toLocaleString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        }),
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app">
      {/* Top bar — corporate nav */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="topbar-logo">
            Regional<span>Tracker</span>
          </div>
          <nav className="topbar-nav">
            <button className="active">Dashboard</button>
            <button>Reports</button>
            <button>Analytics</button>
            <button>Settings</button>
          </nav>
        </div>
        <div className="topbar-right">
          <span className="clock">{clock}</span>
          <div className="topbar-avatar">JR</div>
        </div>
      </header>

      {/* Sub header */}
      <div className="subheader">
        <div>
          <h1>Q1 Regional Performance Tracker</h1>
          <p className="subheader-meta">
            March Madness — NCAA Men's Basketball Tournament 2025-26
          </p>
        </div>
        <span className="subheader-meta">Data via ESPN</span>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'scores' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('scores')}
        >
          Live Metrics
        </button>
        <button
          className={`tab ${activeTab === 'bracket' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('bracket')}
        >
          Bracket Overview
        </button>
      </div>

      {/* Content */}
      {activeTab === 'scores' ? <LiveScores /> : <Bracket />}
    </div>
  );
}
