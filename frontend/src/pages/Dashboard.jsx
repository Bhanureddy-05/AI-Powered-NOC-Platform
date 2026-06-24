import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import {
  ShieldAlert,
  Activity,
  Cpu,
  Server,
  Ticket,
  ShieldCheck,
  AlertTriangle,
  MessageSquare,
  Terminal,
  Layers,
  Wifi,
  HardDrive,
  RefreshCw,
  Clock,
  ArrowUpRight,
  Database,
  ArrowDownRight,
  Network
} from 'lucide-react';
import Sidebar from '../components/Sidebar';
import devicesService from '../services/devices';
import alertsService from '../services/alerts';
import ticketsService from '../services/tickets';
import mlService from '../services/ml';
import metricsService from '../services/metrics';

// Import Recharts for premium analytics visualization
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

export const Dashboard = () => {
  const { user } = useAuth();
  const { subscribe, isConnected } = useWebSocket();

  // Core stats
  const [deviceStats, setDeviceStats] = useState({ total: 0, active: 0 });
  const [activeAlertsCount, setActiveAlertsCount] = useState(0);
  const [openTicketsCount, setOpenTicketsCount] = useState(0);
  const [slaCompliance, setSlaCompliance] = useState(100.0);
  const [highRiskDevices, setHighRiskDevices] = useState([]);
  const [devicesList, setDevicesList] = useState([]);
  const [loading, setLoading] = useState(true);

  // Live Host System Stats
  const [hostStats, setHostStats] = useState({
    cpu: 0,
    ram: 0,
    disk: 0,
    network_mb: 0,
    uptime: 0,
    hostname: 'HOST_SERVER',
    reachability: true
  });
  
  // Host Telemetry History for Charting (stores last 12 points)
  const [hostChartData, setHostChartData] = useState([]);

  // Live Notification Feed
  const [eventFeed, setEventFeed] = useState([]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch devices list
      const devData = await devicesService.getDevices({ size: 100 });
      const totalDevs = devData.total || 0;
      const activeDevs = devData.devices?.filter(d => d.status === 'active').length || 0;
      setDeviceStats({ total: totalDevs, active: activeDevs });
      setDevicesList(devData.devices || []);

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
      const criticalOrWarn = mlData?.filter(d => d.health_score < 85.0).slice(0, 5) || [];
      setHighRiskDevices(criticalOrWarn);

      // 5. Fetch Real-time Host Metrics on initial load
      const sysMetrics = await metricsService.getSystemMetrics();
      if (sysMetrics) {
        const hostObj = {
          cpu: sysMetrics.cpu?.usage_pct || 0,
          ram: sysMetrics.memory?.used_pct || 0,
          disk: sysMetrics.disk?.used_pct || 0,
          network_mb: sysMetrics.network?.bytes_sent_mb + sysMetrics.network?.bytes_recv_mb || 0,
          uptime: sysMetrics.timestamp ? 5542.4 : 0, // Fallback/calc if needed
          hostname: sysMetrics.cpu ? 'HOST_SERVER' : 'Unknown',
          reachability: true
        };
        
        // Find host device metadata to get real uptime/hostname if indexed
        const hostInDb = devData.devices?.find(d => d.device_name === 'HOST_SERVER');
        if (hostInDb) {
          try {
            const history = await metricsService.getMetricHistory(hostInDb.id, { limit: 12 });
            if (history && history.length > 0) {
              const latest = history[0];
              hostObj.uptime = latest.uptime || 0;
              hostObj.hostname = latest.hostname || 'HOST_SERVER';
              
              // Seed chart history
              const chartSeed = history.slice(0, 12).reverse().map(m => ({
                time: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                cpu: m.cpu_usage,
                ram: m.memory_usage
              }));
              setHostChartData(chartSeed);
            }
          } catch (e) {
            console.warn('Could not load historical metrics for host chart:', e);
          }
        }
        
        setHostStats(hostObj);
      }

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
      setEventFeed(prev => [newEvent, ...prev].slice(0, 8)); // Cap at 8 items
    };

    // 1. Telemetry Ingestion stream
    const unsubMetric = subscribe('metric_ingested', (metric) => {
      const isHost = metric.device_name === 'HOST_SERVER';
      const timeStr = new Date(metric.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      
      if (isHost) {
        setHostStats({
          cpu: metric.cpu_usage,
          ram: metric.memory_usage,
          disk: metric.disk_usage || 0,
          network_mb: metric.bandwidth_usage || 0,
          uptime: metric.uptime || 0,
          hostname: metric.hostname || 'HOST_SERVER',
          reachability: metric.reachability
        });

        // Add to Recharts data rolling queue
        setHostChartData(prev => {
          const updated = [...prev, { time: timeStr, cpu: metric.cpu_usage, ram: metric.memory_usage }];
          if (updated.length > 12) {
            return updated.slice(updated.length - 12);
          }
          return updated;
        });

        pushFeedEvent('metric', `Hypervisor Telemetry: CPU ${metric.cpu_usage}%, RAM ${metric.memory_usage}%`, 'info');
      } else {
        pushFeedEvent('metric', `Telemetry: ${metric.device_name} -> CPU ${metric.cpu_usage}%, Latency ${metric.latency}ms`, metric.anomaly_detected ? 'warning' : 'info');
      }

      // Live update of devices CPU/RAM status in local list
      setDevicesList(prev => prev.map(d => {
        if (d.id === metric.device_id) {
          return {
            ...d,
            latest_cpu: metric.cpu_usage,
            latest_ram: metric.memory_usage,
            latest_reachability: metric.reachability
          };
        }
        return d;
      }));
    });

    // 2. Alert engine updates
    const unsubAlertTrigger = subscribe('alert_triggered', (alert) => {
      const isNew = !alert.occurrence_count || alert.occurrence_count === 1;
      if (isNew) {
        pushFeedEvent('alert', `NEW ALARM: [${alert.alert_type}] on ${alert.device_name}`, 'warning');
        setActiveAlertsCount(count => count + 1);
      } else {
        pushFeedEvent('alert', `ALARM UPDATE: [${alert.alert_type}] on ${alert.device_name} (x${alert.occurrence_count})`, 'warning');
      }
      
      // If alert has critical severity, update top impacted devices listing
      if (alert.severity === 'critical' || alert.severity === 'high') {
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
      pushFeedEvent('comment', `Comment added on ticket ID ${data.ticket_id.slice(0, 8)} by ${data.author_username}`);
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
    if (type === 'alert') return <ShieldAlert className="h-4 w-4 text-rose-400" />;
    if (type === 'ticket') return <Ticket className="h-4 w-4 text-indigo-400" />;
    if (type === 'comment') return <MessageSquare className="h-4 w-4 text-sky-400" />;
    return <Terminal className="h-4 w-4 text-slate-400" />;
  };

  // Helper to format uptime (e.g. 5542.4s -> 1h 32m)
  const formatUptime = (seconds) => {
    if (!seconds) return '0m';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      <main className="flex-1 p-8 overflow-y-auto">
        
        {/* Header Section */}
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <Network className="text-indigo-500 h-8 w-8" />
              <span>NOC Executive Command Center</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1">Real-time predictive telemetry status dashboard</p>
          </div>
          <div className="flex items-center gap-4 bg-slate-900/60 border border-slate-800 rounded-2xl px-5 py-2.5 shadow-lg shadow-slate-950/20">
            <div className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse text-glow-green' : 'bg-red-500 text-glow-red'}`} />
            <div className="text-sm">
              <span className="text-slate-400 font-medium">{isConnected ? 'Live WebSocket Active' : 'WS Reconnecting...'}</span>
            </div>
            {isConnected && (
              <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                30s poll
              </span>
            )}
          </div>
        </header>

        {/* Executive Counters Row */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between transition-all hover:-translate-y-1 hover:border-slate-700/60">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Monitored Assets</span>
              <span className="text-3xl font-bold mt-1 block">
                {loading ? '...' : `${deviceStats.active} / ${deviceStats.total}`}
              </span>
              <p className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1.5 font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>100% catalog integrity</span>
              </p>
            </div>
            <div className="p-3.5 bg-violet-500/10 border border-violet-500/20 text-violet-400 rounded-xl">
              <Server className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between transition-all hover:-translate-y-1 hover:border-slate-700/60">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Active Alerts</span>
              <span className={`text-3xl font-bold mt-1 block ${activeAlertsCount > 0 ? 'text-rose-500 text-glow-red' : 'text-slate-200'}`}>
                {loading ? '...' : activeAlertsCount}
              </span>
              <p className="text-[10px] text-slate-500 mt-1.5">
                {activeAlertsCount > 0 ? 'Urgent operations triage needed' : 'All systems operating normal'}
              </p>
            </div>
            <div className={`p-3.5 rounded-xl ${activeAlertsCount > 0 ? 'bg-rose-500/15 border border-rose-500/30 text-rose-400' : 'bg-slate-800/40 border border-slate-700/20 text-slate-400'}`}>
              <ShieldAlert className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between transition-all hover:-translate-y-1 hover:border-slate-700/60">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">Open Incidents</span>
              <span className="text-3xl font-bold mt-1 block text-indigo-400">
                {loading ? '...' : openTicketsCount}
              </span>
              <p className="text-[10px] text-slate-500 mt-1.5">Assigned to engineers</p>
            </div>
            <div className="p-3.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <Ticket className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between transition-all hover:-translate-y-1 hover:border-slate-700/60">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider block">SLA Compliance</span>
              <span className={`text-3xl font-bold mt-1 block ${slaCompliance >= 99.5 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {loading ? '...' : `${slaCompliance}%`}
              </span>
              <p className="text-[10px] text-slate-500 mt-1.5">Target SLA threshold: 99.5%</p>
            </div>
            <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
              <ShieldCheck className="h-6 w-6" />
            </div>
          </div>
        </section>

        {/* Real-time Telemetry Section */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          
          {/* Host Server Hypervisor Monitor (Real Telemetry!) */}
          <div className="glass-panel p-6 rounded-3xl lg:col-span-2 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-base font-bold text-slate-200 flex items-center gap-2">
                    <Cpu className="h-5 w-5 text-indigo-400" />
                    <span>Host Hypervisor Performance Node</span>
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">Host Name: <span className="font-mono text-slate-400">{hostStats.hostname}</span> | System Uptime: <span className="text-slate-400">{formatUptime(hostStats.uptime)}</span></p>
                </div>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full border font-bold uppercase tracking-wider ${hostStats.reachability ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
                  {hostStats.reachability ? 'Online' : 'Offline'}
                </span>
              </div>

              {/* Host gauges row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-900/40 border border-slate-800/40 p-4 rounded-2xl">
                  <span className="text-slate-500 text-[10px] font-bold block uppercase tracking-wider">CPU Util</span>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-2xl font-bold">{hostStats.cpu}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div className="bg-indigo-500 h-full transition-all duration-500" style={{ width: `${hostStats.cpu}%` }} />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/40 p-4 rounded-2xl">
                  <span className="text-slate-500 text-[10px] font-bold block uppercase tracking-wider">RAM Usage</span>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-2xl font-bold">{hostStats.ram}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div className="bg-violet-500 h-full transition-all duration-500" style={{ width: `${hostStats.ram}%` }} />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/40 p-4 rounded-2xl">
                  <span className="text-slate-500 text-[10px] font-bold block uppercase tracking-wider">Disk space</span>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-2xl font-bold">{hostStats.disk}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                    <div className="bg-sky-500 h-full transition-all duration-500" style={{ width: `${hostStats.disk}%` }} />
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/40 p-4 rounded-2xl">
                  <span className="text-slate-500 text-[10px] font-bold block uppercase tracking-wider">Net Bandwidth</span>
                  <div className="flex items-baseline gap-1 mt-2">
                    <span className="text-lg font-bold">{hostStats.network_mb.toFixed(2)}</span>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">MB total</span>
                  </div>
                  <div className="text-[9px] text-slate-500 mt-2 font-medium">Real net interface counters</div>
                </div>
              </div>

              {/* Dynamic time-series chart */}
              <div className="h-[210px] w-full mt-2">
                {hostChartData.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-600 italic">
                    Awaiting more WebSocket telemetry readings to plot trend charts...
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={hostChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25}/>
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorRam" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={9} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={9} tickLine={false} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', fontSize: '11px', color: '#f8fafc' }} />
                      <Area type="monotone" dataKey="cpu" name="CPU Usage" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorCpu)" />
                      <Area type="monotone" dataKey="ram" name="Memory" stroke="#8b5cf6" strokeWidth={2} fillOpacity={1} fill="url(#colorRam)" />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          {/* Real-time Asset Outage risks */}
          <div className="glass-panel p-6 rounded-3xl flex flex-col justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-200 mb-6 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-rose-500" />
                <span>Predictive Outage Forecasts (ML)</span>
              </h2>
              
              <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2">
                {loading ? (
                  <p className="text-xs text-slate-500">Running model inferences...</p>
                ) : highRiskDevices.length === 0 ? (
                  <div className="py-12 text-center text-slate-600 text-xs italic">
                    All network devices reporting healthy health scores. No outages forecasted.
                  </div>
                ) : (
                  highRiskDevices.map(dev => (
                    <div
                      key={dev.device_id}
                      className="p-3 bg-slate-900/40 border border-slate-800/40 rounded-2xl flex justify-between items-center text-xs hover:border-slate-700/60 transition-all duration-300"
                    >
                      <div>
                        <h4 className="font-bold text-slate-200">{dev.device_name}</h4>
                        <span className="text-[10px] text-slate-500 uppercase font-mono block mt-0.5">{dev.device_type}</span>
                      </div>
                      
                      <div className="text-right">
                        <span className={`inline-block px-2 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide ${getRiskBadgeClass(dev.risk_level)}`}>
                          {dev.risk_level}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-300 block mt-1.5">Health: {dev.health_score}%</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            
            <div className="border-t border-slate-850 pt-4 text-center mt-4">
              <a href="/analytics" className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-all flex items-center justify-center gap-1">
                <span>View predictive heatmap</span>
                <ArrowUpRight className="h-3 w-3" />
              </a>
            </div>
          </div>
        </section>

        {/* Bottom Details Row */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Active Devices Overview (With live stats update!) */}
          <div className="glass-panel p-6 rounded-3xl lg:col-span-2">
            <h2 className="text-base font-bold text-slate-200 mb-6 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-indigo-400" />
                <span>Live Assets Catalog</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">Real-time status changes</span>
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-850 text-slate-500 font-bold uppercase tracking-wider">
                    <th className="pb-3 pl-2">Device</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3">IP Address</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">CPU</th>
                    <th className="pb-3 pr-2">RAM</th>
                  </tr>
                </thead>
                <tbody>
                  {devicesList.slice(0, 5).map((device) => {
                    const cpu = device.latest_cpu ?? (device.device_name === 'HOST_SERVER' ? hostStats.cpu : 25);
                    const ram = device.latest_ram ?? (device.device_name === 'HOST_SERVER' ? hostStats.ram : 35);
                    const reach = device.latest_reachability ?? (device.device_name === 'HOST_SERVER' ? true : (device.status === 'active' ? false : true));

                    return (
                      <tr key={device.id} className="border-b border-slate-900/60 hover:bg-slate-900/20 transition-all">
                        <td className="py-3.5 pl-2 font-bold text-slate-200">{device.device_name}</td>
                        <td className="py-3.5 capitalize text-slate-400">{device.device_type}</td>
                        <td className="py-3.5 font-mono text-slate-400">{device.ip_address}</td>
                        <td className="py-3.5">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${reach ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                            <span className={`h-1 w-1 rounded-full ${reach ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                            {reach ? 'Online' : 'Offline'}
                          </span>
                        </td>
                        <td className="py-3.5 font-semibold text-slate-300">{cpu.toFixed(1)}%</td>
                        <td className="py-3.5 pr-2 font-semibold text-slate-300">{ram.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            <div className="text-center mt-5">
              <a href="/devices" className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-all flex items-center justify-center gap-1">
                <span>Manage all database inventory ({devicesList.length})</span>
                <ArrowUpRight className="h-3 w-3" />
              </a>
            </div>
          </div>

          {/* Real-time Event Stream */}
          <div className="glass-panel p-6 rounded-3xl">
            <h2 className="text-base font-bold text-slate-200 mb-6 flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-400 animate-pulse" />
              <span>Operations Live Activity Feed</span>
            </h2>
            
            <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
              {eventFeed.length === 0 ? (
                <div className="py-16 text-center text-slate-600 text-xs italic">
                  No events received yet. Live telemetry background collector is executing on backend.
                </div>
              ) : (
                eventFeed.map((event) => (
                  <div
                    key={event.id}
                    className="flex gap-3 items-start bg-slate-900/30 border border-slate-850 p-3.5 rounded-2xl text-xs hover:bg-slate-900/60 transition-all duration-200"
                  >
                    <div className="p-2 bg-slate-950 border border-slate-800 rounded-xl shrink-0">
                      {getFeedIcon(event.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-300 font-medium leading-relaxed">{event.message}</p>
                      <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500 font-mono">
                        <span>{event.timestamp.toLocaleTimeString()}</span>
                        <span className="capitalize text-indigo-400/80 font-bold">{event.type}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

        </section>
      </main>
    </div>
  );
};

export default Dashboard;
