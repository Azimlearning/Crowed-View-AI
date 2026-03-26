import React from 'react';
import {
  LayoutDashboard, MapPin, Calendar, BarChart2, Settings, HelpCircle
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', active: true },
  { icon: MapPin,          label: 'Venues',    active: false },
  { icon: Calendar,        label: 'Events',    active: false },
  { icon: BarChart2,       label: 'Reports',   active: false },
];

const bottomItems = [
  { icon: Settings,   label: 'Settings',     active: false },
  { icon: HelpCircle, label: 'Help & Support', active: false },
];

const Sidebar = () => {
  return (
    <aside className="sidebar" aria-label="Main navigation">
      {/* Logo / Brand */}
      <div className="sidebar__brand">
        <div className="sidebar__logo-mark" aria-hidden="true">C</div>
        <span className="sidebar__brand-name">CrowdView</span>
      </div>

      {/* Nav */}
      <nav className="sidebar__nav">
        <ul className="sidebar__nav-list" role="list">
          {navItems.map(({ icon: Icon, label, active }) => (
            <li key={label}>
              <button
                className={`sidebar__nav-item ${active ? 'sidebar__nav-item--active' : ''}`}
                aria-current={active ? 'page' : undefined}
                title={label}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Bottom */}
      <div className="sidebar__bottom">
        <ul className="sidebar__nav-list" role="list">
          {bottomItems.map(({ icon: Icon, label }) => (
            <li key={label}>
              <button className="sidebar__nav-item" title={label}>
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
};

export default Sidebar;
