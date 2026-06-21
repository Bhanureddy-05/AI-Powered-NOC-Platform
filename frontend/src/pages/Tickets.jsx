/**
 * pages/Tickets.jsx
 * =================
 * Incident Ticket Management Dashboard
 */

import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import ticketsService from '../services/tickets';
import devicesService from '../services/devices';
import api from '../services/api';
import { useWebSocket } from '../context/WebSocketContext';
import { Ticket, User, Clock, AlertCircle, Plus, Send, CornerDownRight, ShieldCheck, ChevronRight, UserPlus, Search } from 'lucide-react';
import { Toast } from '../components/Toast';

export const Tickets = () => {
  const [tickets, setTickets] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [size] = useState(15);

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [devices, setDevices] = useState([]);
  const [engineers, setEngineers] = useState([]);
  
  // Modals / Drawer
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [history, setHistory] = useState([]);
  const [loadingComments, setLoadingComments] = useState(false);
  
  const [toast, setToast] = useState(null);
  
  // Creation Form State
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [newAssignee, setNewAssignee] = useState('');

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  // Comment Form State
  const [commentText, setCommentText] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);

  const { subscribe } = useWebSocket();

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const data = await ticketsService.getTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        page,
        size
      });
      let list = data.tickets || [];
      if (search) {
        const query = search.toLowerCase();
        list = list.filter(t => 
          t.title.toLowerCase().includes(query) ||
          t.device_name?.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query)
        );
      }
      setTickets(list);
      setTotal(data.total || 0);
      setPages(data.pages || 1);

      const statistics = await ticketsService.getTicketStats();
      setStats(statistics);
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to retrieve tickets data.');
    } finally {
      setLoading(false);
    }
  };

  const fetchMetadata = async () => {
    try {
      const devData = await devicesService.getDevices({ size: 100 });
      setDevices(devData.devices || []);
      
      // Dynamic user/engineer query
      const userRes = await api.get('/auth/users');
      setEngineers(userRes.data || []);
    } catch (err) {
      console.error('Metadata fetch error:', err);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [page, statusFilter, priorityFilter, search]);

  useEffect(() => {
    fetchMetadata();
  }, []);

  // WebSockets synchronization
  useEffect(() => {
    const unsubCreated = subscribe('ticket_created', (newTicket) => {
      setTickets(prev => {
        if (prev.some(t => t.id === newTicket.id)) return prev;
        return [newTicket, ...prev].slice(0, size);
      });
      showToast('info', `NEW TICKET: "${newTicket.title}" has been created.`);
      refreshStats();
    });

    const unsubUpdated = subscribe('ticket_updated', (upTicket) => {
      setTickets(prev => prev.map(t => t.id === upTicket.id ? { ...t, ...upTicket } : t));
      if (selectedTicket?.id === upTicket.id) {
        setSelectedTicket(prev => ({ ...prev, ...upTicket }));
        fetchTicketLogs(upTicket.id);
      }
      refreshStats();
    });

    const unsubCommented = subscribe('ticket_comment_added', (commData) => {
      if (selectedTicket?.id === commData.ticket_id) {
        setComments(prev => [...prev, commData]);
      }
    });

    return () => {
      unsubCreated();
      unsubUpdated();
      unsubCommented();
    };
  }, [subscribe, selectedTicket]);

  const refreshStats = async () => {
    try {
      const statistics = await ticketsService.getTicketStats();
      setStats(statistics);
    } catch (err) {
      console.error(err);
    }
  };

  const showToast = (type, message) => {
    setToast({ type, message });
  };

  const handleSelectTicket = async (ticket) => {
    setSelectedTicket(ticket);
    fetchTicketDetails(ticket.id);
  };

  const fetchTicketDetails = async (id) => {
    setLoadingComments(true);
    try {
      const comms = await ticketsService.getComments(id);
      setComments(comms || []);
      
      const logs = await ticketsService.getTicketHistory(id);
      setHistory(logs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingComments(false);
    }
  };

  const fetchTicketLogs = async (id) => {
    try {
      const logs = await ticketsService.getTicketHistory(id);
      setHistory(logs || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!newTitle || !newDescription || !newDeviceId) {
      showToast('error', 'Please fill in Title, Description, and Device.');
      return;
    }

    try {
      await ticketsService.createTicket({
        title: newTitle,
        description: newDescription,
        device_id: newDeviceId,
        priority: newPriority,
        severity: newPriority,
        assigned_to: newAssignee ? Number(newAssignee) : undefined
      });
      showToast('success', 'Incident ticket raised successfully.');
      setIsCreateOpen(false);
      // Reset form
      setNewTitle('');
      setNewDescription('');
      setNewDeviceId('');
      setNewPriority('medium');
      setNewAssignee('');
      fetchTickets();
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to create ticket.');
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (!selectedTicket) return;
    try {
      const updated = await ticketsService.updateTicket(selectedTicket.id, {
        status: newStatus
      });
      setSelectedTicket(updated);
      fetchTickets();
    } catch (err) {
      console.error(err);
      showToast('error', 'Status transition failed.');
    }
  };

  const handleAssigneeChange = async (newAssigneeId) => {
    if (!selectedTicket) return;
    try {
      const updated = await ticketsService.updateTicket(selectedTicket.id, {
        assigned_to: newAssigneeId ? Number(newAssigneeId) : null
      });
      setSelectedTicket(updated);
      fetchTickets();
    } catch (err) {
      console.error(err);
      showToast('error', 'User assignment failed.');
    }
  };

  const handlePriorityChange = async (newPrio) => {
    if (!selectedTicket) return;
    try {
      const updated = await ticketsService.updateTicket(selectedTicket.id, {
        priority: newPrio,
        severity: newPrio
      });
      setSelectedTicket(updated);
      fetchTickets();
    } catch (err) {
      console.error(err);
      showToast('error', 'Priority modification failed.');
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || !selectedTicket) return;
    
    setSubmittingComment(true);
    try {
      const comm = await ticketsService.addComment(selectedTicket.id, commentText);
      setComments(prev => [...prev, comm]);
      setCommentText('');
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to post comment.');
    } finally {
      setSubmittingComment(false);
    }
  };

  const getPriorityColor = (prio) => {
    const p = prio.toLowerCase();
    if (p === 'critical') return 'bg-red-500/10 border-red-500/20 text-red-400 font-bold';
    if (p === 'high') return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
    if (p === 'medium') return 'bg-violet-500/10 border-violet-500/20 text-violet-400';
    return 'bg-blue-500/10 border-blue-500/20 text-blue-400';
  };

  const getStatusColor = (status) => {
    const s = status.toLowerCase();
    if (s === 'resolved' || s === 'closed') return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
    if (s === 'in_progress' || s === 'assigned') return 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400';
    if (s === 'escalated') return 'bg-red-500/10 border-red-500/20 text-red-400';
    return 'bg-slate-800 border-slate-700 text-slate-300';
  };

  const getSlaBadge = (ticket) => {
    const deadline = new Date(ticket.sla_deadline);
    const now = new Date();
    
    if (ticket.sla_status === 'breached') {
      return <span className="inline-block px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-bold">BREACHED</span>;
    }
    if (ticket.sla_status === 'met') {
      return <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">MET</span>;
    }

    const diff = deadline - now;
    if (diff <= 0) {
      return <span className="inline-block px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-bold">BREACHED</span>;
    }
    
    // Format hours remaining
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    
    const isClose = hours < 2;
    return (
      <span className={`inline-block px-1.5 py-0.5 rounded font-mono ${isClose ? 'bg-amber-500/10 border-amber-500/20 text-amber-400 font-semibold' : 'bg-slate-800 border-slate-700 text-slate-400'}`}>
        {hours}h {minutes}m
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto flex gap-6">
        
        {/* Left Column - Incidents Feed */}
        <div className="flex-1 min-w-0">
          {toast && (
            <Toast
              type={toast.type}
              message={toast.message}
              onClose={() => setToast(null)}
            />
          )}

          <header className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold">Incident Ticket Management</h1>
              <p className="text-slate-400 text-sm mt-1">Assign, audit, and track service level agreements (SLAs) for system outages</p>
            </div>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="bg-violet-600 hover:bg-violet-500 text-white font-semibold py-2.5 px-5 rounded-xl transition-all shadow-[0_0_15px_rgba(124,58,237,0.2)] flex items-center gap-2 hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] text-sm"
            >
              <Plus className="h-4 w-4" />
              <span>Raise Ticket</span>
            </button>
          </header>

          {/* Ticket Stats Highlight Panel */}
          {stats && (
            <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="glass-panel px-5 py-4 rounded-xl">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Incidents</span>
                <span className="text-xl font-bold text-slate-200">{stats.total}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-amber-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Active Escalated</span>
                <span className="text-xl font-bold text-amber-400">{stats.escalated}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-red-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">SLA Breaches</span>
                <span className="text-xl font-bold text-red-400">{stats.sla_breached}</span>
              </div>
              <div className="glass-panel px-5 py-4 rounded-xl border-l-2 border-l-emerald-500">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">SLA Compliant</span>
                <span className="text-xl font-bold text-emerald-400">{stats.sla_met}</span>
              </div>
            </section>
          )}

          {/* Filter Toolbar */}
          <section className="glass-panel p-4 rounded-xl mb-6 flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search titles, descriptions, devices..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-violet-500/50 placeholder:text-slate-500"
              />
            </div>
            
            <div className="flex gap-4 w-full md:w-auto">
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-300 focus:outline-none focus:border-violet-500/50 cursor-pointer"
              >
                <option value="">All Priorities</option>
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
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
                <option value="escalated">Escalated</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </section>

          {/* Tickets List */}
          <section className="glass-panel rounded-xl overflow-hidden mb-6">
            <div className="overflow-y-auto max-h-[600px]">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/60 border-b border-slate-800 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
                    <th className="py-3 px-6">Incident Details</th>
                    <th className="py-3 px-6">Device</th>
                    <th className="py-3 px-4">Priority</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">SLA Countdown</th>
                    <th className="py-3 px-6">Assignee</th>
                    <th className="py-3 px-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 text-sm">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">
                        Loading incident tickets...
                      </td>
                    </tr>
                  ) : tickets.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">
                        No incident tickets found.
                      </td>
                    </tr>
                  ) : (
                    tickets.map((ticket) => (
                      <tr
                        key={ticket.id}
                        onClick={() => handleSelectTicket(ticket)}
                        className={`hover:bg-slate-900/40 transition-all cursor-pointer ${selectedTicket?.id === ticket.id ? 'bg-violet-600/5 border-l-2 border-l-violet-500' : ''}`}
                      >
                        <td className="py-3.5 px-6">
                          <span className="font-semibold text-slate-200 block text-xs truncate max-w-xs">{ticket.title}</span>
                          <span className="text-[10px] text-slate-500 block truncate max-w-xs mt-0.5">{ticket.id.substring(0, 8)}... | {ticket.description}</span>
                        </td>
                        <td className="py-3.5 px-6 font-medium text-slate-300 text-xs">
                          {ticket.device_name}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-block px-2 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide ${getPriorityColor(ticket.priority)}`}>
                            {ticket.priority}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`inline-block px-2 py-0.5 border rounded text-[9px] font-semibold uppercase ${getStatusColor(ticket.status)}`}>
                            {ticket.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-xs font-semibold">
                          {getSlaBadge(ticket)}
                        </td>
                        <td className="py-3.5 px-6 font-medium text-slate-400 text-xs flex items-center gap-2">
                          <User className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                          <span>{ticket.assignee_username || 'Unassigned'}</span>
                        </td>
                        <td className="py-3.5 px-2">
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

        {/* Right Column - Incident Drawer */}
        {selectedTicket && (
          <div className="w-[420px] shrink-0 glass-panel rounded-3xl p-6 flex flex-col justify-between self-start shadow-2xl border border-slate-800/80 max-h-[800px] overflow-y-auto animate-slide-in">
            <div>
              <header className="flex justify-between items-start mb-6 pb-4 border-b border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Ticket Details</span>
                  <h2 className="text-base font-bold text-slate-100 mt-0.5 leading-tight">{selectedTicket.title}</h2>
                </div>
                <button
                  onClick={() => setSelectedTicket(null)}
                  className="text-slate-500 hover:text-slate-300 text-xs font-semibold px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg shrink-0"
                >
                  Close
                </button>
              </header>

              {/* Status and Configuration Settings */}
              <div className="grid grid-cols-2 gap-4 mb-6 border-b border-slate-800 pb-6 text-xs">
                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Lifecycle Status</label>
                  <select
                    value={selectedTicket.status}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 font-semibold focus:outline-none focus:border-violet-500 cursor-pointer"
                  >
                    <option value="open">Open</option>
                    <option value="assigned">Assigned</option>
                    <option value="in_progress">In Progress</option>
                    <option value="escalated">Escalated</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Assignee</label>
                  <select
                    value={selectedTicket.assigned_to || ''}
                    onChange={(e) => handleAssigneeChange(e.target.value || null)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 font-semibold focus:outline-none focus:border-violet-500 cursor-pointer"
                  >
                    <option value="">Unassigned</option>
                    {engineers.map(e => (
                      <option key={e.id} value={e.id}>{e.username}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Priority</label>
                  <select
                    value={selectedTicket.priority}
                    onChange={(e) => handlePriorityChange(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 font-semibold focus:outline-none focus:border-violet-500 cursor-pointer"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">SLA Countdown</label>
                  <div className="bg-slate-900 border border-slate-800 rounded-lg p-2 flex items-center justify-between font-semibold h-[34px]">
                    <Clock className="h-3.5 w-3.5 text-slate-500" />
                    <span>{getSlaBadge(selectedTicket)}</span>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="mb-6 border-b border-slate-800 pb-6">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1.5">Description Summary</span>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 border border-slate-800/60 p-3 rounded-xl">
                  {selectedTicket.description}
                </p>
                <span className="text-[9px] text-slate-500 block mt-2 font-mono">Device: {selectedTicket.device_name}</span>
              </div>

              {/* Comments Section */}
              <div className="mb-6">
                <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-3">Incident Commentary Logs</h3>
                
                {loadingComments ? (
                  <p className="text-xs text-slate-500">Querying comment threads...</p>
                ) : (
                  <div className="space-y-3 max-h-48 overflow-y-auto mb-4 border-b border-slate-800/40 pb-4">
                    {comments.length === 0 ? (
                      <p className="text-xs text-slate-600 italic">No notes posted yet. Submit a comment to log updates.</p>
                    ) : (
                      comments.map(c => (
                        <div key={c.id} className="bg-slate-900/50 border border-slate-800/40 p-2.5 rounded-xl text-xs">
                          <div className="flex justify-between items-center text-[10px] text-slate-500 mb-1">
                            <span className="font-bold text-slate-400">{c.author_username}</span>
                            <span className="font-mono">{new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                          <p className="text-slate-300">{c.comment}</p>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Comment Submission Form */}
                <form onSubmit={handleAddComment} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Type comments, actions performed..."
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-violet-500/50 text-slate-100 placeholder:text-slate-600"
                  />
                  <button
                    type="submit"
                    disabled={submittingComment || !commentText.trim()}
                    className="bg-violet-600 hover:bg-violet-500 text-white p-2.5 rounded-xl transition-all disabled:opacity-40"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </form>
              </div>

              {/* History Audit Trail */}
              <div>
                <h3 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-3">Ticket Activity Trail</h3>
                <div className="space-y-3 max-h-32 overflow-y-auto relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-800 text-[10px]">
                  {history.map(log => (
                    <div key={log.id} className="flex gap-3 relative pl-1">
                      <div className="h-4 w-4 rounded-full bg-slate-950 border border-slate-800 shrink-0 flex items-center justify-center z-10">
                        <CornerDownRight className="h-2 w-2 text-indigo-400" />
                      </div>
                      <div>
                        <p className="text-slate-300">
                          Modified <span className="font-semibold text-slate-400 font-mono">{log.field_changed}</span> from <span className="text-slate-500 line-through">{log.old_value || 'n/a'}</span> to <span className="text-indigo-400 font-semibold">{log.new_value}</span>
                        </p>
                        <span className="text-[9px] text-slate-600 block mt-0.5">
                          by {log.user_username} at {new Date(log.changed_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Create Ticket Modal */}
        {isCreateOpen && (
          <div className="fixed inset-0 bg-slate-950/80 backdrop-filter backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="glass-panel w-full max-w-lg rounded-3xl p-8 border border-slate-800 shadow-2xl animate-slide-in">
              <header className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold">Raise Incident Ticket</h2>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-slate-500 hover:text-slate-300 text-xs font-semibold px-2.5 py-1 bg-slate-900 border border-slate-800 rounded-lg"
                >
                  Cancel
                </button>
              </header>

              <form onSubmit={handleCreateTicket} className="space-y-4 text-xs">
                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CORE-ROUTER-A High Packet Loss"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm focus:outline-none focus:border-violet-500/50 placeholder:text-slate-600"
                  />
                </div>

                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Description Summary</label>
                  <textarea
                    rows="3"
                    required
                    placeholder="Describe findings, metric values, and trigger conditions..."
                    value={newDescription}
                    onChange={(e) => setNewDescription(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 text-sm focus:outline-none focus:border-violet-500/50 placeholder:text-slate-600 resize-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Target Device</label>
                    <select
                      required
                      value={newDeviceId}
                      onChange={(e) => setNewDeviceId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-violet-500 cursor-pointer"
                    >
                      <option value="">Select Device...</option>
                      {devices.map(d => (
                        <option key={d.id} value={d.id}>{d.device_name} ({d.ip_address})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Initial Priority</label>
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-violet-500 cursor-pointer"
                    >
                      <option value="low">Low (24h SLA)</option>
                      <option value="medium">Medium (12h SLA)</option>
                      <option value="high">High (4h/240m SLA)</option>
                      <option value="critical">Critical (2h/120m SLA)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Initial Assignee</label>
                  <select
                    value={newAssignee}
                    onChange={(e) => setNewAssignee(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-violet-500 cursor-pointer"
                  >
                    <option value="">Leave Unassigned</option>
                    {engineers.map(e => (
                      <option key={e.id} value={e.id}>{e.username}</option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  className="w-full bg-violet-600 hover:bg-violet-500 text-white font-semibold py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(124,58,237,0.2)] hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] text-sm mt-6"
                >
                  Create Incident Ticket
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Tickets;
