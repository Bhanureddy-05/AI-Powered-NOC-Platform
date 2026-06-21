/**
 * pages/Reports.jsx
 * =================
 * Reports & Data Exports Interface
 */

import React, { useEffect, useState } from 'react';
import Sidebar from '../components/Sidebar';
import reportsService from '../services/reports';
import { FileText, Download, Calendar, Activity, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Toast } from '../components/Toast';

export const Reports = () => {
  const [days, setDays] = useState(7);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloadingFormat, setDownloadingFormat] = useState(null); // 'pdf' or 'csv'
  const [csvType, setCsvType] = useState('metrics'); // 'metrics', 'alerts', 'tickets'
  const [toast, setToast] = useState(null);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const data = await reportsService.getReportSummary(days);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load report summary:', err);
      showToast('error', 'Failed to retrieve report summary data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [days]);

  const showToast = (type, message) => {
    setToast({ type, message });
  };

  const handleDownloadPdf = async () => {
    setDownloadingFormat('pdf');
    try {
      await reportsService.downloadReport(null, 'pdf', days);
      showToast('success', 'PDF Report compiled and downloaded successfully.');
    } catch (err) {
      console.error('Failed to download PDF report:', err);
      showToast('error', 'PDF compilation failed. Please verify system logs.');
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDownloadCsv = async () => {
    setDownloadingFormat('csv');
    try {
      await reportsService.downloadReport(csvType, 'csv', days);
      showToast('success', `CSV dataset for ${csvType} exported successfully.`);
    } catch (err) {
      console.error('Failed to download CSV:', err);
      showToast('error', `CSV export for ${csvType} failed.`);
    } finally {
      setDownloadingFormat(null);
    }
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
            <h1 className="text-3xl font-bold">Reporting & Exports</h1>
            <p className="text-slate-400 text-sm mt-1">Compile PDF summaries and export CSV datasets of NOC operations</p>
          </div>
          <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2">
            <Calendar className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-medium text-slate-300">Period: </span>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-transparent border-none text-violet-400 text-sm font-semibold focus:outline-none cursor-pointer"
            >
              <option value={1} className="bg-slate-900 text-slate-100">Last 24 Hours</option>
              <option value={7} className="bg-slate-900 text-slate-100">Last 7 Days</option>
              <option value={30} className="bg-slate-900 text-slate-100">Last 30 Days</option>
              <option value={90} className="bg-slate-900 text-slate-100">Last 90 Days</option>
            </select>
          </div>
        </header>

        {/* Overview Statistics Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Overall SLA Compliance</span>
              <div className="text-3xl font-bold text-emerald-400 mt-1">
                {loading ? '...' : `${summary?.sla_compliance_pct}%`}
              </div>
              <p className="text-xs text-slate-500 mt-1">Target threshold: 99.5%</p>
            </div>
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
              <ShieldCheck className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Telemetry Alerts</span>
              <div className="text-3xl font-bold text-violet-400 mt-1">
                {loading ? '...' : summary?.total_alerts}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {loading ? '' : `${summary?.resolved_alerts_pct}% resolved`}
              </p>
            </div>
            <div className="p-3 bg-violet-500/10 border border-violet-500/20 text-violet-400 rounded-xl">
              <AlertTriangle className="h-6 w-6" />
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Avg Latency Response</span>
              <div className="text-3xl font-bold text-indigo-400 mt-1">
                {loading ? '...' : `${summary?.average_latency_ms} ms`}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {loading ? '' : `Packet loss: ${summary?.average_packet_loss_pct}%`}
              </p>
            </div>
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <Activity className="h-6 w-6" />
            </div>
          </div>
        </section>

        {/* Action Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* PDF compilation card */}
          <div className="glass-panel p-8 rounded-3xl flex flex-col justify-between">
            <div>
              <div className="p-4 bg-violet-600/10 border border-violet-500/20 text-violet-400 rounded-2xl w-fit mb-6">
                <FileText className="h-8 w-8" />
              </div>
              <h2 className="text-xl font-bold mb-2">Executive Operations PDF Report</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Generates a print-ready executive summary. The document highlights device inventory counts, 
                average CPU/Memory load trends, resolved alert indices, open critical incidents, and SLA compliance scores.
              </p>
            </div>
            <button
              onClick={handleDownloadPdf}
              disabled={loading || downloadingFormat !== null}
              className="w-full bg-violet-600 hover:bg-violet-500 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-[0_0_20px_rgba(124,58,237,0.2)] hover:shadow-[0_0_25px_rgba(124,58,237,0.3)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Download className="h-4 w-4" />
              <span>
                {downloadingFormat === 'pdf' ? 'Compiling PDF...' : 'Download PDF Summary'}
              </span>
            </button>
          </div>

          {/* CSV exporter card */}
          <div className="glass-panel p-8 rounded-3xl flex flex-col justify-between">
            <div>
              <div className="p-4 bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 rounded-2xl w-fit mb-6">
                <Download className="h-8 w-8" />
              </div>
              <h2 className="text-xl font-bold mb-2">Spreadsheet Raw Dataset Export</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Export telemetry, active triggers, or incident records into a standard CSV format. 
                Excellent for analysis in Microsoft Excel, Pandas, or external logging software.
              </p>

              {/* CSV Selection */}
              <div className="space-y-3 mb-8">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Dataset Category</label>
                <div className="grid grid-cols-3 gap-3">
                  {['metrics', 'alerts', 'tickets'].map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setCsvType(type)}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold uppercase tracking-wider transition-all ${
                        csvType === type
                          ? 'bg-indigo-600/10 text-indigo-400 border-indigo-500/30'
                          : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-900/60 hover:text-slate-100'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={handleDownloadCsv}
              disabled={loading || downloadingFormat !== null}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-4 rounded-xl transition-all shadow-[0_0_20px_rgba(79,70,229,0.2)] hover:shadow-[0_0_25px_rgba(79,70,229,0.3)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Download className="h-4 w-4" />
              <span>
                {downloadingFormat === 'csv' ? 'Exporting CSV...' : `Download ${csvType} CSV`}
              </span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Reports;
