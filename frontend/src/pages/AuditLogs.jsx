/**
 * pages/AuditLogs.jsx
 * ===================
 * Security & Auditing Interface
 */

import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import auditService from '../services/audit';
import { Shield, Search, ArrowLeft, ArrowRight, UserCheck, ShieldAlert, Cpu } from 'lucide-react';
import { Toast } from '../components/Toast';

export const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [size] = useState(25);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  // Filters
  const [usernameFilter, setUsernameFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [ipFilter, setIpFilter] = useState('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await auditService.getAuditLogs({
        username: usernameFilter || undefined,
        action: actionFilter || undefined,
        ip_address: ipFilter || undefined,
        page,
        size
      });
      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);

      const statsData = await auditService.getAuditLogStats();
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
      if (err.response && err.response.status === 403) {
        setToast({ type: 'error', message: 'RBAC: Access Denied. Admins only.' });
      } else {
        setToast({ type: 'error', message: 'Failed to fetch audit log logs.' });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page, usernameFilter, actionFilter, ipFilter]);

  const getActionBadgeClass = (action) => {
    const act = action.toLowerCase();
    if (act.includes('fail') || act.includes('deleted')) {
      return 'bg-red-500/10 border-red-500/20 text-red-400';
    }
    if (act.includes('success') || act.includes('register') || act.includes('created') || act.includes('resolved')) {
      return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
    }
    if (act.includes('update')) {
      return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
    }
    return 'bg-slate-800 border-slate-700 text-slate-300';
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">
        {toast && (
          <Toast
            type={toast.type}
            message={toast.message}
            onClose={() => setToast(null)}
          />
        )}
        
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Shield className="h-8 w-8 text-violet-400" />
              <span>Security & Audit Logs</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1">Immutable tracking of operator logins, database CRUD events, and security exceptions</p>
          </div>
        </header>

        {/* Audit Stats Highlights */}
        {stats && (
          <section className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
              <div className="p-3 bg-violet-500/10 text-violet-400 rounded-xl">
                <Shield className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Total Audits</span>
                <span className="text-2xl font-bold">{stats.total_events}</span>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
                <UserCheck className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Logins (24h)</span>
                <span className="text-2xl font-bold">{stats.logins_success_24h}</span>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
              <div className="p-3 bg-red-500/10 text-red-400 rounded-xl">
                <ShieldAlert className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Failed Logins (24h)</span>
                <span className="text-2xl font-bold text-red-400">{stats.logins_failed_24h}</span>
              </div>
            </div>

            <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Device Configs (24h)</span>
                <span className="text-2xl font-bold">{stats.device_operations_24h}</span>
              </div>
            </div>
          </section>
        )}

        {/* Filter Toolbar */}
        <section className="glass-panel p-6 rounded-2xl mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Filter by Username..."
              value={usernameFilter}
              onChange={(e) => { setUsernameFilter(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-slate-500"
            />
          </div>

          <div>
            <select
              value={actionFilter}
              onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-violet-500/50 transition-all cursor-pointer"
            >
              <option value="">All Action Categories</option>
              <option value="login_success">login_success</option>
              <option value="login_failed">login_failed</option>
              <option value="user_registered">user_registered</option>
              <option value="device_created">device_created</option>
              <option value="device_updated">device_updated</option>
              <option value="device_deleted">device_deleted</option>
              <option value="alert_status_updated">alert_status_updated</option>
              <option value="ticket_created">ticket_created</option>
              <option value="ticket_updated">ticket_updated</option>
              <option value="ticket_comment_added">ticket_comment_added</option>
            </select>
          </div>

          <div>
            <input
              type="text"
              placeholder="Filter by IP Address..."
              value={ipFilter}
              onChange={(e) => { setIpFilter(e.target.value); setPage(1); }}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-violet-500/50 transition-all placeholder:text-slate-500"
            />
          </div>
        </section>

        {/* Logs Table */}
        <section className="glass-panel rounded-2xl overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900/60 border-b border-slate-800 text-slate-400 text-xs font-bold uppercase tracking-wider">
                  <th className="py-4 px-6">Timestamp</th>
                  <th className="py-4 px-6">User / Actor</th>
                  <th className="py-4 px-6">Action Category</th>
                  <th className="py-4 px-6">Operation Details</th>
                  <th className="py-4 px-6">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-sm text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      Loading audit database records...
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      No matching audit log entries found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-900/20 transition-all">
                      <td className="py-3.5 px-6 font-mono text-xs text-slate-400">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3.5 px-6 font-semibold text-slate-200">
                        {log.username}
                      </td>
                      <td className="py-3.5 px-6">
                        <span className={`inline-block px-2 py-0.5 border rounded text-[11px] font-bold uppercase tracking-wider ${getActionBadgeClass(log.action)}`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 max-w-md truncate text-xs text-slate-400" title={log.details}>
                        {log.details}
                      </td>
                      <td className="py-3.5 px-6 font-mono text-xs text-slate-400">
                        {log.ip_address || 'n/a'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Pagination controls */}
        {pages > 1 && (
          <div className="flex justify-between items-center bg-slate-900/25 border border-slate-800/40 rounded-xl p-4">
            <span className="text-xs text-slate-400 font-medium">
              Showing logs page <strong className="text-slate-200">{page}</strong> of <strong className="text-slate-200">{pages}</strong> ({total} entries total)
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-100 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-all"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
              <button
                disabled={page >= pages}
                onClick={() => setPage(p => Math.min(pages, p + 1))}
                className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-100 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-all"
              >
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AuditLogs;
