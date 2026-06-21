/**
 * pages/Analytics.jsx
 * ===================
 * AI/ML Analytics & Capacity Forecasting Dashboard
 */

import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import mlService from '../services/ml';
import { useAuth } from '../context/AuthContext';
import { Cpu, TrendingUp, AlertOctagon, RefreshCw, BarChart2, CheckCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Toast } from '../components/Toast';

export const Analytics = () => {
  const { user } = useAuth();
  
  const [predictions, setPredictions] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [details, setDetails] = useState(null);
  
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchPredictions = async () => {
    setLoading(true);
    try {
      const data = await mlService.getPredictions();
      setPredictions(data || []);
      
      // Auto-select first high-risk device if any
      if (data && data.length > 0) {
        handleSelectDevice(data[0].device_id);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to retrieve telemetry prediction results.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDevice = async (deviceId) => {
    setLoadingDetails(true);
    try {
      const devDetails = await mlService.getPredictionDetails(deviceId);
      setDetails(devDetails);
      
      // Keep track of which device object was selected
      const devObj = predictions.find(p => p.device_id === deviceId);
      if (devObj) {
        setSelectedDevice(devObj);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      const res = await mlService.retrainModels();
      showToast('success', `Retraining success! Models fitted on ${res.metrics_trained} records.`);
      fetchPredictions();
    } catch (err) {
      console.error(err);
      showToast('error', 'Retraining pipeline execution failed.');
    } finally {
      setRetraining(false);
    }
  };

  const showToast = (type, message) => {
    setToast({ type, message });
  };

  useEffect(() => {
    fetchPredictions();
  }, []);

  const getRiskColor = (risk) => {
    const r = risk.toLowerCase();
    if (r === 'critical') return 'text-red-400 border-red-500/20 bg-red-500/5';
    if (r === 'medium') return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
    return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
  };

  const getHeatmapColor = (risk) => {
    const r = risk.toLowerCase();
    if (r === 'critical') return 'bg-red-500 border-red-400 hover:shadow-[0_0_15px_#ef4444]';
    if (r === 'medium') return 'bg-amber-500 border-amber-400 hover:shadow-[0_0_15px_#f59e0b]';
    return 'bg-emerald-500 border-emerald-400 hover:shadow-[0_0_15px_#10b981]';
  };

  // Formulate data points for Recharts capacity forecaster
  const getForecastChartData = () => {
    if (!details || !details.forecast) return [];
    return details.forecast.map(point => ({
      time: new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      'Predicted CPU (%)': point.cpu_usage_predicted,
      'Predicted Bandwidth (Mbps)': point.bandwidth_usage_predicted
    }));
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
        
        <header className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Cpu className="h-8 w-8 text-violet-400 animate-pulse" />
              <span>Predictive ML Analytics</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1">Telemetry anomaly detection and capacity trend projections using scikit-learn Isolation Forests and Random Forests</p>
          </div>
          
          {/* Retrain Action Button */}
          {(user?.role === 'admin' || user?.role === 'operator') && (
            <button
              onClick={handleRetrain}
              disabled={retraining || loading}
              className="bg-violet-600 hover:bg-violet-500 text-white font-semibold py-2.5 px-5 rounded-xl transition-all shadow-[0_0_15px_rgba(124,58,237,0.2)] flex items-center gap-2 hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] text-sm disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${retraining ? 'animate-spin' : ''}`} />
              <span>{retraining ? 'Retraining Models...' : 'Retrain ML Models'}</span>
            </button>
          )}
        </header>

        {/* heat map / risk overview */}
        <section className="glass-panel p-6 rounded-3xl mb-8">
          <h2 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-indigo-400" />
            <span>NOC Asset Risk Heatmap</span>
          </h2>
          <div className="flex flex-wrap gap-3">
            {loading ? (
              <span className="text-slate-500 text-sm">Compiling asset maps...</span>
            ) : predictions.length === 0 ? (
              <span className="text-slate-500 text-sm">No device telemetry cataloged.</span>
            ) : (
              predictions.map(dev => (
                <button
                  key={dev.device_id}
                  onClick={() => handleSelectDevice(dev.device_id)}
                  title={`${dev.device_name} | Health: ${dev.health_score}% | Risk: ${dev.risk_level.toUpperCase()}`}
                  className={`h-10 px-3 border rounded-xl flex items-center gap-2 text-xs font-semibold text-slate-100 transition-all shrink-0 cursor-pointer ${
                    details?.device_id === dev.device_id
                      ? 'bg-slate-900 ring-2 ring-violet-500/60 border-slate-700'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900'
                  }`}
                >
                  <div className={`h-2.5 w-2.5 rounded-full border ${getHeatmapColor(dev.risk_level)}`} />
                  <span>{dev.device_name}</span>
                </button>
              ))
            )}
          </div>
        </section>

        {/* main workspace layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Panel: Devices ranking by Health Score */}
          <div className="glass-panel p-6 rounded-3xl self-start max-h-[600px] overflow-y-auto">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Device Health Ranking</h3>
            <div className="space-y-3">
              {loading ? (
                <p className="text-xs text-slate-500">Querying health records...</p>
              ) : predictions.map((dev) => (
                <div
                  key={dev.device_id}
                  onClick={() => handleSelectDevice(dev.device_id)}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex justify-between items-center ${
                    details?.device_id === dev.device_id
                      ? 'bg-slate-900/90 border-slate-700 shadow-md'
                      : 'bg-slate-900/40 border-slate-800/60 hover:bg-slate-900/60'
                  }`}
                >
                  <div>
                    <h4 className="text-xs font-bold text-slate-200">{dev.device_name}</h4>
                    <span className="text-[10px] text-slate-500 block uppercase tracking-wide mt-0.5">{dev.device_type}</span>
                  </div>
                  
                  <div className="text-right">
                    <span className={`inline-block px-1.5 py-0.5 border rounded text-[9px] font-bold uppercase tracking-wide ${getRiskColor(dev.risk_level)}`}>
                      {dev.risk_level}
                    </span>
                    <div className="text-xs font-bold text-slate-200 mt-1">{dev.health_score}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Panel: Selected Device Prediction Details and Capacity Chart */}
          <div className="lg:col-span-2 space-y-8">
            {loadingDetails ? (
              <div className="glass-panel p-8 rounded-3xl h-[450px] flex items-center justify-center text-slate-500 text-sm">
                Running ML diagnostics on device telemetry...
              </div>
            ) : details ? (
              <>
                {/* Highlights row */}
                <div className="glass-panel p-6 rounded-3xl grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center md:border-r border-slate-800/80 md:pr-4">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Health score</span>
                    <span className={`text-3xl font-extrabold block ${details.health_score > 80 ? 'text-emerald-400' : details.health_score > 50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {details.health_score}%
                    </span>
                    <span className="text-[10px] text-slate-500 mt-1 block">Failure prob: {details.failure_probability}</span>
                  </div>

                  <div className="text-center md:border-r border-slate-800/80 md:px-4">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Anomalies (24h)</span>
                    <span className="text-3xl font-extrabold text-violet-400 block">
                      {details.anomalies_count_24h}
                    </span>
                    <span className="text-[10px] text-slate-500 mt-1 block">Flagged by Isolation Forest</span>
                  </div>

                  <div className="text-center md:pl-4">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-1">Maintenance action</span>
                    <span className={`text-sm font-bold uppercase tracking-wider mt-2.5 inline-block px-3 py-1 rounded-full border ${
                      details.maintenance_status === 'good'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : details.maintenance_status === 'warning'
                          ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                          : 'bg-red-500/10 border-red-500/20 text-red-400 font-bold animate-pulse'
                    }`}>
                      {details.maintenance_status === 'good' ? 'Healthy' : details.maintenance_status === 'warning' ? 'Schedule Check' : 'CRITICAL OUTAGE'}
                    </span>
                  </div>
                </div>

                {/* Capacity prediction chart */}
                <div className="glass-panel p-6 rounded-3xl">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-6 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-violet-400" />
                    <span>24-Hour Capacity Trend Projections ({details.device_name})</span>
                  </h3>
                  
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={getForecastChartData()}
                        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                        <YAxis stroke="#64748b" fontSize={10} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            border: '1px solid #334155',
                            borderRadius: '12px',
                            color: '#f8fafc',
                            fontSize: '11px'
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                        <Line
                          type="monotone"
                          dataKey="Predicted CPU (%)"
                          stroke="#7c3aed"
                          strokeWidth={2}
                          dot={false}
                        />
                        <Line
                          type="monotone"
                          dataKey="Predicted Bandwidth (Mbps)"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </>
            ) : (
              <div className="glass-panel p-8 rounded-3xl h-[450px] flex items-center justify-center text-slate-500 text-sm">
                No active device predictions populated. Verify simulator seeder.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Analytics;
