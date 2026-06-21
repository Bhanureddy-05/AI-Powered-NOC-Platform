/**
 * components/Sidebar.jsx
 * =======================
 * Reusable Sidebar Navigation Layout Component
 * 
 * WHY THIS FILE EXISTS:
 *     Centralizes application-wide navigation. Highlights active tabs dynamically
 *     based on the client route, preventing code duplication across screens.
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, Activity, Cpu, Server, Ticket, LogOut, FileText, Shield, MessageSquareCode } from 'lucide-react';

export const Sidebar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  // Helper function to check active path for styling
  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: Activity },
    { name: 'Devices', path: '/devices', icon: Server },
    { name: 'Alerts', path: '/alerts', icon: ShieldAlert },
    { name: 'Tickets', path: '/tickets', icon: Ticket },
    { name: 'Analytics', path: '/analytics', icon: Cpu },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'AI Copilot', path: '/copilot', icon: MessageSquareCode },
  ];

  // Append Audit Logs option dynamically for Admin role
  const visibleNavItems = [...navItems];
  if (user?.role === 'admin') {
    visibleNavItems.push({ name: 'Audit Logs', path: '/audit-logs', icon: Shield });
  }

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/40 p-6 flex flex-col justify-between shrink-0">
      <div>
        <Link to="/" className="flex items-center gap-2 font-bold text-lg text-violet-400 mb-8 hover:text-violet-300 transition-all">
          <ShieldAlert className="h-6 w-6" />
          <span>AETHER NOC</span>
        </Link>
        <nav className="space-y-2">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all font-medium ${
                  active
                    ? 'bg-violet-600/10 text-violet-400 font-semibold border border-violet-500/20 shadow-[0_0_15px_rgba(124,58,237,0.05)]'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>


      <div className="space-y-4">
        {user && (
          <div className="p-3 bg-slate-900/40 border border-slate-800/60 rounded-xl">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Account</p>
            <p className="text-sm font-semibold text-slate-300 truncate mt-1">{user.username}</p>
            <span className="inline-block mt-1 text-[10px] font-bold px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-violet-400 uppercase tracking-wide">
              {user.role}
            </span>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all w-full text-left font-medium"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
