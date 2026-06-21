/**
 * pages/Dashboard.jsx
 * ===================
 * Executive NOC Command Center Dashboard
 */

import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { ShieldAlert, Activity, Cpu, Server, Ticket, ShieldCheck, AlertTriangle, MessageSquare, Terminal } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import devicesService from '../services/devices';
import alertsService from '../services/alerts';
import ticketsService from '../services/tickets';
import mlService from '../services/ml';

export const Dashboard = () => {
  const { user } = useAuth();
  const { subscribe, isConnected } = useWebSocket();

  // Core stats
  const [deviceStats, setDeviceStats] = useState({ total: 0, active: 0 });
  const [activeAlertsCount, setActiveAlertsCount] = useState(0);
  const [openTicketsCount, setOpenTicketsCount] = useState(0);
  const [slaCompliance, setSlaCompliance] = useState(100.0);
  const [highRiskDevices, setHighRiskDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  // Live Notification Feed
  const [eventFeed, setEventFeed] = useState([]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch devices
      const devData = await devicesService.getDevices({ size: 100 });
      const totalDevs = devData.total || 0;
      const activeDevs = devData.devices?.filter(d => d.status === 'active').length || 0;
      setDeviceStats({ total: totalDevs, active: activeDevs });

      // 2. Fetch alert stats
      const alertStats = await alertsService.getAlertStats();
      setActiveAlertsCount(alertStats.open + alertStats.acknowledged + alertStats.investigating);

      // 3. Fetch ticket stats
      const ticketStats = await ticketsService.getTicketStats();
      setOpenTicketsCount(ticketStats.open + ticketStats.assigned + ticketStats.in_progress + ticketStats.escalated);
      
      const met = ticketStats.sla_met || 0;
      const breached = ticketStats.sla_breached || 0;
      const totalSla = met + breached;
      if (totalSla > 0) {
        setSlaCompliance(Number(((met / totalSla) * 100).toFixed(1)));
      } else {
        setSlaCompliance(100.0);
      }

      // 4. Fetch top ML predictions
      const mlData = await mlService.getPredictions();
      // Filter devices with health score < 85% as high risk
      const criticalOrWarn = mlData?.filter(d => d.health_score < 85.0).slice(0, 5) || [];
      setHighRiskDevices(criticalOrWarn);

    } catch (error) {
      console.error('Failed to load dashboard statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // WebSockets integrations for real-time dashboard hot-reloading
  useEffect(() => {
    const pushFeedEvent = (type, message, severity = 'info') => {
      const newEvent = {
        id: Math.random().toString(),
        type,
        message,
        severity,
        timestamp: new Date()
      };
      setEventFeed(prev => [newEvent, ...prev].slice(0, 10)); // Cap at 10 items
    };

    // 1. Telemetry Ingestion stream
    const unsubMetric = subscribe('metric_ingested', (metric) => {
      pushFeedEvent('metric', `Telemetry: ${metric.device_name} -> CPU ${metric.cpu_usage}%, RAM ${metric.memory_usage}%`);
      
      // Update monitored devices counters dynamically
      setDeviceStats(prev => ({ ...prev, active: prev.active }));
    });

    // 2. Alert engine updates
    const unsubAlertTrigger = subscribe('alert_triggered', (alert) => {
      pushFeedEvent('alert', `NEW ALARM: [${alert.alert_type}] on ${alert.device_name}`, 'warning');
      setActiveAlertsCount(count => count + 1);
      
      // If alert has critical severity, update top impacted devices listing
      if (alert.severity === 'critical' || alert.severity === 'high') {
        // Refetch predictions to update risk heatmap lists
        mlService.getPredictions().then(data => {
          setHighRiskDevices(data?.filter(d => d.health_score < 85.0).slice(0, 5) || []);
        });
      }
    });

    const unsubAlertAck = subscribe('alert_acknowledged', (data) => {
      pushFeedEvent('alert', `Alarm Acknowledged: ID ${data.id.slice(0, 8)} by operator`);
    });

    const unsubAlertResolve = subscribe('alert_resolved', (data) => {
      pushFeedEvent('alert', `Alarm Resolved: ID ${data.id.slice(0, 8)}`);
      setActiveAlertsCount(count => Math.max(0, count - 1));
    });

    // 3. Ticketing lifecycle updates
    const unsubTicketCreate = subscribe('ticket_created', (ticket) => {
      pushFeedEvent('ticket', `Ticket Raised: "${ticket.title}"`, 'info');
      setOpenTicketsCount(count => count + 1);
    });

    const unsubTicketUpdate = subscribe('ticket_updated', (ticket) => {
      pushFeedEvent('ticket', `Ticket Status: "${ticket.title}" changed to ${ticket.status.toUpperCase()}`);
      if (ticket.status === 'resolved' || ticket.status === 'closed') {
        setOpenTicketsCount(count => Math.max(0, count - 1));
        // Refetch stats to update SLA metrics
        ticketsService.getTicketStats().then(stats => {
          const met = stats.sla_met || 0;
          const breached = stats.sla_breached || 0;
          const totalSla = met + breached;
          if (totalSla > 0) {
            setSlaCompliance(Number(((met / totalSla) * 100).toFixed(1)));
          }
        });
      }
    });

    const unsubTicketComment = subscribe('ticket_comment_added', (data) => {
      pushFeedEvent('comment', `Comment Added on ticket: "${data.comment.slice(0, 30)}..." by ${data.author_username}`);
    });

    return () => {
      unsubMetric();
      unsubAlertTrigger();
      unsubAlertAck();
      unsubAlertResolve();
      unsubTicketCreate();
      unsubTicketUpdate();
      unsubTicketComment();
    };
  }, [subscribe]);

  const getRiskBadgeClass = (level) => {
    const l = level.toLowerCase();
    if (l === 'critical') return 'bg-red-500/10 border-red-500/20 text-red-400 font-bold';
    if (l === 'medium') return 'bg-amber-500/10 border-amber-500/20 text-amber-400';
    return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
  };

  const getFeedIcon = (type) => {
    if (type === 'alert') return <ShieldAlert className="h-4 w-4 text-amber-400" />;
    if (type === 'ticket') return <Ticket className="h-4 w-4 text-indigo-400" />;
    if (type === 'comment') return <MessageSquare className="h-4 w-4 text-sky-400" />;
    return <Terminal className="h-4 w-4 text-slate-500" />;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">
        
        {/* Header Section */}
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <span>NOC Command Center</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1">Real-time predictive telemetry status dashboard</p>
          </div>
          <div className="flex items-center gap-4 bg-slate-900/60 border border-slate-800 rounded-2xl px-5 py-2.5">
            <div className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <div className="text-sm">
              <span className="text-slate-400">{isConnected ? 'Live Socket Connected' : 'Connecting Socket...'}</span>
            </div>
          </div>
        </header>

        {/* Executive Counters Row */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Monitored Assets</span>
              <span className="text-2xl font-bold mt-1 block">
                {loading ? '...' : `${deviceStats.active} / ${deviceStats.total}`}
              </span>
              <p className="text-xs text-slate-500 mt-1">Active nodes online</p>
            </div>
            <div className="p-3.5 bg-violet-500/10 border border-violet-500/20 text-violet-400 rounded-xl">
              <Server className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Active Alerts</span>
              <span className={`text-2xl font-bold mt-1 block ${activeAlertsCount > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                {loading ? '...' : activeAlertsCount}
              </span>
              <p className="text-xs text-slate-500 mt-1">Requires response</p>
            </div>
            <div className="p-3.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl">
              <ShieldAlert className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Open Tickets</span>
              <span className="text-2xl font-bold mt-1 block text-indigo-400">
                {loading ? '...' : openTicketsCount}
              </span>
              <p className="text-xs text-slate-500 mt-1">Assigned to engineers</p>
            </div>
            <div className="p-3.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <Ticket className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">SLA Compliance</span>
              <span className="text-2xl font-bold mt-1 block text-emerald-400">
                {loading ? '...' : `${slaCompliance}%`}
              </span>
              <p className="text-xs text-slate-500 mt-1">Target threshold: 99.5%</p>
            </div>
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
              <ShieldCheck className="h-6 w-6" />
            </div>
          </div>
        </section>

        {/* Dashboard Panels Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Live Activity Feed Ticker (WebSockets broadcast log) */}
          <div className="glass-panel p-6 rounded-3xl lg:col-span-2">
            <h2 className="text-base font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Activity className="h-5 w-5 text-violet-400 animate-pulse" />
              <span>Real-time NOC Event Stream</span>
            </h2>
            
            <div className="space-y-4 max-h-[420px] overflow-y-auto pr-2">
              {eventFeed.length === 0 ? (
                <div className="py-12 text-center text-slate-600 text-xs italic">
                  Awaiting websocket transmission events... Start the metric generator simulation script.
                </div>
              ) : (
                eventFeed.map((event) => (
                  <div
                    key={event.id}
                    className="flex gap-3 items-start bg-slate-900/40 border border-slate-800/40 p-3 rounded-2xl text-xs transition-all hover:bg-slate-900/60"
                  >
                    <div className="p-2 bg-slate-950 border border-slate-800 rounded-lg shrink-0">
                      {getFeedIcon(event.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-300 font-medium leading-relaxed">{event.message}</p>
                      <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                        {event.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Top High-Risk Devices list */}
          <div className="glass-panel p-6 rounded-3xl">
            <h2 className="text-base font-bold text-slate-200 mb-6 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <span>Predictive Outage Risks</span>
            </h2>
            
            <div className="space-y-3">
              {loading ? (
                <p className="text-xs text-slate-500">Querying failure probabilities...</p>
              ) : highRiskDevices.length === 0 ? (
                <div className="py-8 text-center text-slate-600 text-xs italic">
                  No critical device outages forecasted. All nodes healthy.
                </div>
              ) : (
                highRiskDevices.map(dev => (
                  <div
                    key={dev.device_id}
                    className="p-3 bg-slate-900/45 border border-slate-800/60 rounded-2xl flex justify-between items-center text-xs hover:border-slate-700 transition-all"
                  >
                    <div>
                      <h4 className="font-bold text-slate-200">{dev.device_name}</h4>
                      <span className="text-[10px] text-slate-500 uppercase block mt-0.5">{dev.device_type}</span>
                    </div>
                    
                    <div className="text-right">
                      <span className={`inline-block px-1.5 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide ${getRiskBadgeClass(dev.risk_level)}`}>
                        {dev.risk_level}
                      </span>
                      <span className="text-xs font-bold text-slate-200 block mt-1">Health: {dev.health_score}%</span>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            <div className="mt-6 border-t border-slate-800 pt-4 text-center">
              <a href="/analytics" className="text-xs font-semibold text-violet-400 hover:text-violet-300 transition-all">
                Open Detailed Analytics &rarr;
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
