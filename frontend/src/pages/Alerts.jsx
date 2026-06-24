/**
 * pages/Alerts.jsx
 * =================
 * Alert Management Engine Dashboard
 */

import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import alertsService from '../services/alerts';
import { useWebSocket } from '../context/WebSocketContext';
import { ShieldAlert, CheckCircle, Search, AlertCircle, Clock, FileText, ChevronRight, CornerDownRight } from 'lucide-react';
import { Toast } from '../components/Toast';

const formatDuration = (firstSeen, lastSeen) => {
  if (!firstSeen || !lastSeen) return '0s';
  const start = new Date(firstSeen);
  const end = new Date(lastSeen);
  const diffMs = end - start;
  if (diffMs < 0) return '0s';
  
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays}d ${diffHours % 24}h ${diffMins % 60}m`;
  }
  if (diffHours > 0) {
    return `${diffHours}h ${diffMins % 60}m`;
  }
  if (diffMins > 0) {
    return `${diffMins}m ${diffSecs % 60}s`;
  }
  return `${diffSecs}s`;
};

const formatTime = (dateStr) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
};

export const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [size] = useState(15);
  
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [toast, setToast] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  // Action fields
  const [actionNotes, setActionNotes] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  const { subscribe } = useWebSocket();

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const data = await alertsService.getAlerts({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        page,
        size
      });
      // Filter list on client using search key if present
      let list = data.alerts || [];
      if (search) {
        const query = search.toLowerCase();
        list = list.filter(a => 
          a.alert_type.toLowerCase().includes(query) ||
          a.device_name?.toLowerCase().includes(query) ||
          a.message.toLowerCase().includes(query)
        );
      }
      setAlerts(list);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
      
      const statistics = await alertsService.getAlertStats();
      setStats(statistics);
    } catch (err) {
      console.error('Failed to query alerts:', err);
      showToast('error', 'Failed to retrieve alerts database records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [page, statusFilter, severityFilter, search]);

  // Setup WebSocket Listeners for real-time alerting
  useEffect(() => {
    const unsubTriggered = subscribe('alert_triggered', (newAlert) => {
      setAlerts(prev => {
        if (prev.some(a => a.id === newAlert.id)) {
          // Update the existing alert in place with new occurrence count, last_seen, message, severity, etc.
          return prev.map(a => a.id === newAlert.id ? { ...a, ...newAlert } : a);
        }
        return [newAlert, ...prev].slice(0, size);
      });
      setSelectedAlert(prev => {
        if (prev && prev.id === newAlert.id) {
          return { ...prev, ...newAlert };
        }
        return prev;
      });
      const isNew = !newAlert.occurrence_count || newAlert.occurrence_count === 1;
      if (isNew) {
        showToast('warning', `NEW ALERT: ${newAlert.alert_type} on device! (${newAlert.severity.toUpperCase()})`);
      } else {
        showToast('warning', `ALERT UPDATE: ${newAlert.alert_type} (x${newAlert.occurrence_count})`);
      }
      refreshStats();
    });

    const unsubAcked = subscribe('alert_acknowledged', (ackData) => {
      setAlerts(prev => prev.map(a => a.id === ackData.id ? { ...a, status: 'acknowledged' } : a));
      if (selectedAlert?.id === ackData.id) {
        setSelectedAlert(prev => ({ ...prev, status: 'acknowledged' }));
        fetchAlertHistory(ackData.id);
      }
      refreshStats();
    });

    const unsubResolved = subscribe('alert_resolved', (resData) => {
      setAlerts(prev => prev.map(a => a.id === resData.id ? { ...a, status: 'resolved', resolved: true } : a));
      if (selectedAlert?.id === resData.id) {
        setSelectedAlert(prev => ({ ...prev, status: 'resolved', resolved: true }));
        fetchAlertHistory(resData.id);
      }
      refreshStats();
    });

    return () => {
      unsubTriggered();
      unsubAcked();
      unsubResolved();
    };
  }, [subscribe, selectedAlert]);

  const refreshStats = async () => {
    try {
      const statistics = await alertsService.getAlertStats();
      setStats(statistics);
    } catch (err) {
      console.error(err);
    }
  };

  const showToast = (type, message) => {
    setToast({ type, message });
  };

  const handleSelectAlert = async (alert) => {
    setSelectedAlert(alert);
    fetchAlertHistory(alert.id);
  };

  const fetchAlertHistory = async (alertId) => {
    setLoadingHistory(true);
    try {
      const logs = await alertsService.getAlertHistory(alertId);
      setHistory(logs || []);
    } catch (err) {
      console.error('Failed to fetch alert history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!selectedAlert) return;
    setSubmittingAction(true);
    try {
      const updated = await alertsService.acknowledgeAlert(selectedAlert.id, actionNotes);
      setSelectedAlert(updated);
      setActionNotes('');
      showToast('success', 'Alert acknowledged successfully.');
      fetchAlerts();
    } catch (err) {
      console.error(err);
      showToast('error', 'Acknowledge failed.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedAlert) return;
    setSubmittingAction(true);
    try {
      const updated = await alertsService.resolveAlert(selectedAlert.id, actionNotes);
      setSelectedAlert(updated);
      setActionNotes('');
      showToast('success', 'Alert resolved.');
      fetchAlerts();
    } catch (err) {
      console.error(err);
      showToast('error', 'Resolve failed.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const getSeverityColor = (severity) => {
    const sev = severity.toLowerCase();
    if (sev === 'critical') return 'bg-red-500/10 border-red-500/20 text-red-400 font-bold';
    if (sev === 'high') return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
    if (sev === 'medium') return 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400';
    return 'bg-blue-500/10 border-blue-500/20 text-blue-400';
  };

  const getStatusColor = (status) => {
    const s = status.toLowerCase();
    if (s === 'resolved') return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
    if (s === 'acknowledged') return 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400';
    if (s === 'investigating') return 'bg-sky-500/10 border-sky-500/20 text-sky-400';
    return 'bg-red-500/10 border-red-500/20 text-red-400';
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto flex gap-6">
        
        {/* Left Column - Alerts Feed */}
        <div className="flex-1 min-w-0">
          {toast && (
            <Toast
              type={toast.type}
              message={toast.message}
              onClose={() => setToast(null)}
            />
          )}

          <header className="flex justify-between items-start mb-8">
            <div>
              <h1 className="text-3xl font-bold">Alert Management Engine</h1>
              <p className="text-slate-400 text-sm mt-1">Audit active alarms and historical network anomalies</p>
            </div>
          </header>

          {/* Alert Statistics Mini-Grid */}
          {stats && (
            <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="glass-panel px-5 py-4 rounded-xl">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Active</span>
                <span className="text-xl font-bold text-slate-200">{stats.open + stats.acknowledged + stats.investigating}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-red-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Critical Severity</span>
                <span className="text-xl font-bold text-red-400">{stats.critical}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-amber-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">High Severity</span>
                <span className="text-xl font-bold text-amber-400">{stats.high}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-emerald-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Resolved Alarm</span>
                <span className="text-xl font-bold text-emerald-400">{stats.resolved}</span>
              </div>
            </section>
          )}

          {/* Filter Toolbar */}
          <section className="glass-panel p-4 rounded-xl mb-6 flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search type, message, device..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-violet-500/50 placeholder:text-slate-500"
              />
            </div>
            
            <div className="flex gap-4 w-full md:w-auto">
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:border-violet-500/50 cursor-pointer"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:border-violet-500/50 cursor-pointer"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="acknowledged">Acknowledged</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </section>

          {/* Alerts Feed List */}
          <section className="glass-panel rounded-xl overflow-hidden mb-6">
            <div className="overflow-y-auto max-h-[600px]">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/60 border-b border-slate-800 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-6">Alert Trigger</th>
                    <th className="py-3 px-6">Device</th>
                    <th className="py-3 px-6">Severity</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Age</th>
                    <th className="py-3 px-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-sm">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-500">
                        Loading active telemetry alarms...
                      </td>
                    </tr>
                  ) : alerts.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-500">
                        No active anomalies triggered.
                      </td>
                    </tr>
                  ) : (
                    alerts.map((alert) => (
                      <tr
                        key={alert.id}
                        onClick={() => handleSelectAlert(alert)}
                        className={`hover:bg-slate-900/40 transition-all cursor-pointer ${selectedAlert?.id === alert.id ? 'bg-violet-600/5 border-l-2 border-l-violet-500' : ''}`}
                      >
                        <td className="py-3 px-6">
                          <span className="font-semibold text-slate-200 block text-xs">
                            {alert.alert_type}
                            {alert.occurrence_count > 1 && (
                              <span className="ml-2 bg-slate-800 border border-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full text-[9px] font-bold">
                                x{alert.occurrence_count}
                              </span>
                            )}
                          </span>
                          <span className="text-[11px] text-slate-500 block truncate max-w-xs mt-0.5">{alert.message}</span>
                        </td>
                        <td className="py-3 px-6 font-medium text-slate-300 text-xs">
                          {alert.device_name}
                        </td>
                        <td className="py-3 px-6">
                          <span className={`inline-block px-2 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide ${getSeverityColor(alert.severity)}`}>
                            {alert.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-block px-2 py-0.5 border rounded text-[9px] font-semibold uppercase ${getStatusColor(alert.status)}`}>
                            {alert.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[10px] text-slate-500">
                          {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="py-3 px-2">
                          <ChevronRight className="h-4 w-4 text-slate-600" />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* Right Column - Alert Slide-over Detail Panel */}
        {selectedAlert && (
          <div className="w-96 shrink-0 glass-panel rounded-3xl p-6 flex flex-col justify-between self-start shadow-2xl border border-slate-800/80 animate-slide-in">
            <div>
              <header className="flex justify-between items-start mb-6">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Telemetry Diagnostic</span>
                  <h2 className="text-lg font-bold text-slate-100 mt-0.5">{selectedAlert.alert_type}</h2>
                </div>
                <button
                  onClick={() => setSelectedAlert(null)}
                  className="text-slate-500 hover:text-slate-300 text-xs font-semibold px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg"
                >
                  Close
                </button>
              </header>

              {/* Alert Details summary list */}
              <div className="space-y-4 mb-6 border-b border-slate-800/80 pb-6 text-xs">
                <div>
                  <span className="text-slate-500 font-semibold block">Device Target</span>
                  <span className="text-slate-300 font-medium">{selectedAlert.device_name} ({selectedAlert.device_ip})</span>
                </div>
                <div>
                  <span className="text-slate-500 font-semibold block">Trigger Condition</span>
                  <span className="text-slate-300 font-medium leading-relaxed">{selectedAlert.message}</span>
                </div>
                <div className="flex justify-between items-center bg-slate-900/60 border border-slate-800/50 p-2.5 rounded-xl">
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase tracking-wider font-bold">Severity</span>
                    <span className={`inline-block px-1.5 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide mt-1 ${getSeverityColor(selectedAlert.severity)}`}>
                      {selectedAlert.severity}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[9px] uppercase tracking-wider font-bold">Lifecycle</span>
                    <span className={`inline-block px-1.5 py-0.5 border rounded text-[9px] font-bold uppercase mt-1 ${getStatusColor(selectedAlert.status)}`}>
                      {selectedAlert.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Deduplication & Lifetime Summary */}
              <div className="mb-6 border-b border-slate-800/80 pb-6 text-xs">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Deduplication & Lifetime</h3>
                <div className="grid grid-cols-2 gap-3 bg-slate-900/40 border border-slate-800/50 p-3 rounded-xl">
                  <div>
                    <span className="text-slate-500 block text-[10px] font-medium">Occurrences</span>
                    <span className="text-slate-200 font-semibold text-sm">{selectedAlert.occurrence_count || 1}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] font-medium">Duration</span>
                    <span className="text-violet-400 font-semibold text-sm">
                      {formatDuration(selectedAlert.first_seen || selectedAlert.timestamp, selectedAlert.last_seen || selectedAlert.timestamp)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] font-medium">First Seen</span>
                    <span className="text-slate-300 font-medium">{formatTime(selectedAlert.first_seen || selectedAlert.timestamp)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] font-medium">Last Seen</span>
                    <span className="text-slate-300 font-medium">{formatTime(selectedAlert.last_seen || selectedAlert.timestamp)}</span>
                  </div>
                </div>
              </div>

              {/* Audit Timeline / History */}
              <div className="mb-6">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Audit Transition Trail</h3>
                
                {loadingHistory ? (
                  <p className="text-xs text-slate-500">Querying historical logs...</p>
                ) : history.length === 0 ? (
                  <p className="text-xs text-slate-500">No transition records registered.</p>
                ) : (
                  <div className="space-y-3 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-800">
                    {history.map((log) => (
                      <div key={log.id} className="flex gap-3 text-[11px] relative">
                        <div className="h-4 w-4 rounded-full bg-slate-900 border border-slate-800 shrink-0 flex items-center justify-center z-10">
                          <CornerDownRight className="h-2.5 w-2.5 text-violet-400" />
                        </div>
                        <div>
                          <p className="text-slate-300 font-medium">
                            Status: <span className="font-bold text-violet-400 capitalize">{log.status_to}</span>
                          </p>
                          {log.notes && <p className="text-slate-500 mt-0.5">{log.notes}</p>}
                          <span className="text-[10px] text-slate-600 block mt-1">
                            {new Date(log.changed_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Operations panel */}
            {selectedAlert.status !== 'resolved' && (
              <div className="border-t border-slate-800/80 pt-6">
                <textarea
                  rows="2"
                  placeholder="Enter resolution actions or notes..."
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs focus:outline-none focus:border-violet-500/50 mb-3 text-slate-100 placeholder:text-slate-600 resize-none"
                />
                
                {selectedAlert.status === 'open' ? (
                  <button
                    onClick={handleAcknowledge}
                    disabled={submittingAction}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl text-xs transition-all disabled:opacity-50"
                  >
                    Acknowledge Alert
                  </button>
                ) : (
                  <button
                    onClick={handleResolve}
                    disabled={submittingAction}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 rounded-xl text-xs transition-all disabled:opacity-50"
                  >
                    Resolve Alert
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default Alerts;
