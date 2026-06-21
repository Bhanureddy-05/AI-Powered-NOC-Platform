/**
 * pages/Devices.jsx
 * =================
 * Phase 3 Device Inventory Management View
 * 
 * WHY THIS FILE EXISTS:
 *     Serves as the main inventory management board for NOC engineers.
 *     Allows viewing, creating, updating, and removing network assets (Cisco routers,
 *     switches, firewalls, etc.) based on RBAC constraints.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import devicesService from '../services/devices';
import Sidebar from '../components/Sidebar';
import { ToastContainer } from '../components/Toast';
import {
  Search,
  Filter,
  Plus,
  Edit2,
  Trash2,
  Eye,
  X,
  ChevronLeft,
  ChevronRight,
  Copy,
  Check,
  Server,
  Network,
  Shield,
  Cpu,
  AlertTriangle,
  RefreshCw,
  Clock,
  MapPin,
  Globe
} from 'lucide-react';

export const Devices = () => {
  const { user } = useAuth();

  // Role permissions helpers
  const canWrite = user?.role === 'admin' || user?.role === 'operator';
  const canDelete = user?.role === 'admin';

  // State Declarations
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalDevices, setTotalDevices] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Selected device for inspector drawer
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  // Modals configurations
  // activeModal format: { mode: 'create' | 'edit', data: null | deviceData }
  const [activeModal, setActiveModal] = useState(null);
  // deleteConfirm format: null | deviceData
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  // Form states (Create / Edit)
  const [formName, setFormName] = useState('');
  const [formIp, setFormIp] = useState('');
  const [formLocation, setFormLocation] = useState('');
  const [formType, setFormType] = useState('router');
  const [formStatus, setFormStatus] = useState('active');
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  // Toast notifications state
  const [toasts, setToasts] = useState([]);

  // Toast notifications helpers
  const addToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
  };
  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // 1. Fetch devices handler
  const fetchDevices = async () => {
    setLoading(true);
    try {
      const response = await devicesService.getDevices({
        q: searchQuery || undefined,
        device_type: filterType || undefined,
        status: filterStatus || undefined,
        page,
        size: pageSize
      });
      setDevices(response.devices || []);
      setTotalDevices(response.total || 0);
      setTotalPages(response.pages || 1);
    } catch (error) {
      console.error('Failed to load device inventory:', error);
      addToast(
        error.response?.data?.detail || 'Failed to load device database.',
        'error'
      );
    } finally {
      setLoading(false);
    }
  };

  // Debounce query inputs to avoid hammering the backend
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      setPage(1); // Reset page on filter/search change
      fetchDevices();
    }, 350);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery, filterType, filterStatus]);

  // Handle page switches separately without debounce
  useEffect(() => {
    fetchDevices();
  }, [page, pageSize]);

  // Helper: Copy details to clipboard
  const copyToClipboard = (text, fieldName) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
    addToast(`${fieldName} copied to clipboard!`, 'info');
  };

  // Helper: Validate IP formats in JavaScript
  const validateIpAddress = (ip) => {
    const ipv4Regex = /^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$/;
    return ipv4Regex.test(ip) || ipv6Regex.test(ip);
  };

  // Open Modal Helper (resets form values)
  const openModal = (mode, data = null) => {
    setActiveModal({ mode, data });
    if (mode === 'edit' && data) {
      setFormName(data.device_name);
      setFormIp(data.ip_address);
      setFormLocation(data.location || '');
      setFormType(data.device_type);
      setFormStatus(data.status);
    } else {
      setFormName('');
      setFormIp('');
      setFormLocation('');
      setFormType('router');
      setFormStatus('active');
    }
    setFormErrors({});
  };

  // Handle Form Submission (Add & Edit)
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormErrors({});

    // Client-side validations
    const errors = {};
    if (!formName.trim() || formName.length < 3) {
      errors.name = 'Device name must be at least 3 characters.';
    }
    if (!formIp.trim() || !validateIpAddress(formIp.trim())) {
      errors.ip = 'Please specify a valid IPv4 or IPv6 address.';
    }
    if (formLocation.length > 100) {
      errors.location = 'Location detail cannot exceed 100 characters.';
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setSubmitting(true);
    const payload = {
      device_name: formName.trim(),
      ip_address: formIp.trim(),
      location: formLocation.trim() || null,
      device_type: formType,
      status: formStatus
    };

    try {
      if (activeModal.mode === 'create') {
        const result = await devicesService.createDevice(payload);
        addToast(`Registered device ${result.device_name} successfully!`, 'success');
      } else if (activeModal.mode === 'edit') {
        const result = await devicesService.updateDevice(activeModal.data.id, payload);
        addToast(`Updated device ${result.device_name} configuration.`, 'success');
        if (selectedDevice?.id === result.id) {
          setSelectedDevice(result); // sync details drawer
        }
      }
      setActiveModal(null);
      fetchDevices();
    } catch (error) {
      console.error('API operation failed:', error);
      const detail = error.response?.data?.detail;
      const backendMessage = Array.isArray(detail) ? detail[0]?.msg : detail;
      addToast(backendMessage || 'Save failed. Verify inputs and try again.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Device Deletion (Admin only)
  const handleDeleteSubmit = async () => {
    if (!deleteConfirm) return;
    setSubmitting(true);
    try {
      await devicesService.deleteDevice(deleteConfirm.id);
      addToast(`Removed ${deleteConfirm.device_name} from inventory.`, 'success');
      if (selectedDevice?.id === deleteConfirm.id) {
        setSelectedDevice(null); // Close detail drawer
      }
      setDeleteConfirm(null);
      fetchDevices();
    } catch (error) {
      console.error('Delete request failed:', error);
      addToast(
        error.response?.data?.detail || 'Failed to delete device from database.',
        'error'
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Device type indicators helper (returns color classes & icon)
  const getTypeBadge = (type) => {
    const config = {
      router: {
        icon: <Network className="h-4.5 w-4.5 shrink-0" />,
        style: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
      },
      switch: {
        icon: <Server className="h-4.5 w-4.5 shrink-0" />,
        style: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
      },
      firewall: {
        icon: <Shield className="h-4.5 w-4.5 shrink-0" />,
        style: 'bg-rose-500/10 text-rose-400 border-rose-500/20'
      },
      server: {
        icon: <Cpu className="h-4.5 w-4.5 shrink-0" />,
        style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      }
    };

    return config[type.toLowerCase()] || {
      icon: <Server className="h-4.5 w-4.5 shrink-0" />,
      style: 'bg-slate-500/10 text-slate-400 border-slate-500/20'
    };
  };

  // Device status badge styling helper
  const getStatusBadge = (status) => {
    const config = {
      active: {
        dot: 'bg-emerald-500',
        style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-glow-green',
        ping: true
      },
      inactive: {
        dot: 'bg-rose-500',
        style: 'bg-rose-500/10 text-rose-400 border-rose-500/20 text-glow-red',
        ping: false
      },
      maintenance: {
        dot: 'bg-amber-500',
        style: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        ping: false
      }
    };

    return config[status.toLowerCase()] || {
      dot: 'bg-slate-500',
      style: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
      ping: false
    };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex relative overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main dashboard content */}
      <main className="flex-1 p-8 overflow-y-auto z-10">
        <header className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold">Device Inventory</h1>
            <p className="text-slate-400 text-sm mt-1">
              Add, audit, and configure Cisco network assets in the Aether NOC grid.
            </p>
          </div>
          {canWrite && (
            <button
              onClick={() => openModal('create')}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_0_20px_rgba(124,58,237,0.25)] transition-all active:scale-95 shrink-0 self-start sm:self-auto"
            >
              <Plus className="h-5 w-5" />
              <span>Register Device</span>
            </button>
          )}
        </header>

        {/* Filter controls */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center gap-4 mb-6">
          <div className="relative w-full md:flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500" />
            <input
              type="text"
              placeholder="Search by device name, IP address, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-11 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm placeholder-slate-500 outline-none transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          <div className="flex w-full md:w-auto items-center gap-3">
            <div className="flex-1 md:w-44">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm outline-none transition-all text-slate-300"
              >
                <option value="">All Types</option>
                <option value="router">Router</option>
                <option value="switch">Switch</option>
                <option value="firewall">Firewall</option>
                <option value="server">Server</option>
              </select>
            </div>
            <div className="flex-1 md:w-44">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm outline-none transition-all text-slate-300"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="maintenance">Maintenance</option>
              </select>
            </div>
            <button
              onClick={() => {
                setSearchQuery('');
                setFilterType('');
                setFilterStatus('');
              }}
              title="Reset Filters"
              className="p-2.5 bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 rounded-xl transition-all"
            >
              <RefreshCw className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Devices list representation */}
        <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-800/60 bg-slate-900/30 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="px-6 py-4.5">Device Name</th>
                  <th className="px-6 py-4.5">IP Address</th>
                  <th className="px-6 py-4.5">Device Type</th>
                  <th className="px-6 py-4.5">Location</th>
                  <th className="px-6 py-4.5">Operational Status</th>
                  <th className="px-6 py-4.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-sm">
                {loading ? (
                  // Skeleton Rows Loader
                  Array.from({ length: pageSize }).map((_, idx) => (
                    <tr key={idx} className="animate-pulse">
                      <td className="px-6 py-4">
                        <div className="h-5 bg-slate-900 rounded w-32" />
                      </td>
                      <td className="px-6 py-4">
                        <div className="h-5 bg-slate-900 rounded w-28" />
                      </td>
                      <td className="px-6 py-4">
                        <div className="h-6 bg-slate-900 rounded w-20" />
                      </td>
                      <td className="px-6 py-4">
                        <div className="h-5 bg-slate-900 rounded w-24" />
                      </td>
                      <td className="px-6 py-4">
                        <div className="h-6 bg-slate-900 rounded w-24" />
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="h-5 bg-slate-900 rounded w-16 ml-auto" />
                      </td>
                    </tr>
                  ))
                ) : devices.length === 0 ? (
                  // Empty State
                  <tr>
                    <td colSpan="6" className="text-center py-16 px-6">
                      <div className="flex flex-col items-center justify-center max-w-sm mx-auto">
                        <div className="h-12 w-12 rounded-full bg-slate-900/80 border border-slate-800 flex items-center justify-center text-slate-500 mb-4">
                          <AlertTriangle className="h-6 w-6" />
                        </div>
                        <h3 className="text-lg font-semibold text-slate-200">No devices found</h3>
                        <p className="text-slate-400 text-xs mt-1 text-center">
                          No registered device details matched your current filter criteria or query string.
                        </p>
                        {(searchQuery || filterType || filterStatus) && (
                          <button
                            onClick={() => {
                              setSearchQuery('');
                              setFilterType('');
                              setFilterStatus('');
                            }}
                            className="mt-4 text-xs font-semibold text-violet-400 hover:text-violet-300 hover:underline"
                          >
                            Reset searches & filters
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  // Data Rendering
                  devices.map((device) => {
                    const typeBadge = getTypeBadge(device.device_type);
                    const statusBadge = getStatusBadge(device.status);
                    return (
                      <tr
                        key={device.id}
                        className={`hover:bg-slate-900/35 transition-colors cursor-pointer group ${
                          selectedDevice?.id === device.id ? 'bg-violet-950/15 border-l-2 border-l-violet-500' : ''
                        }`}
                        onClick={() => setSelectedDevice(device)}
                      >
                        <td className="px-6 py-4 font-semibold text-slate-200">
                          {device.device_name}
                        </td>
                        <td className="px-6 py-4 font-mono text-slate-400 text-xs">
                          {device.ip_address}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold uppercase tracking-wide ${typeBadge.style}`}>
                            {typeBadge.icon}
                            <span>{device.device_type}</span>
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-400">
                          {device.location || <span className="text-slate-600 font-mono text-xs">-</span>}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold capitalize ${statusBadge.style}`}>
                            <span className="relative flex h-2 w-2">
                              {statusBadge.ping && (
                                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusBadge.dot}`} />
                              )}
                              <span className={`relative inline-flex rounded-full h-2 w-2 ${statusBadge.dot}`} />
                            </span>
                            <span>{device.status}</span>
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex justify-end items-center gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setSelectedDevice(device)}
                              title="Details View"
                              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            {canWrite && (
                              <button
                                onClick={() => openModal('edit', device)}
                                title="Edit Configuration"
                                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-violet-400 transition-all"
                              >
                                <Edit2 className="h-4 w-4" />
                              </button>
                            )}
                            {canDelete && (
                              <button
                                onClick={() => setDeleteConfirm(device)}
                                title="Remove Device"
                                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800/80 hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-all"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-slate-800/60 bg-slate-900/10 flex flex-col sm:flex-row justify-between items-center gap-4">
              <div className="text-xs text-slate-400">
                Showing <span className="font-semibold text-slate-200">{(page - 1) * pageSize + 1}</span> to{' '}
                <span className="font-semibold text-slate-200">
                  {Math.min(page * pageSize, totalDevices)}
                </span>{' '}
                of <span className="font-semibold text-slate-200">{totalDevices}</span> devices
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs inline-flex items-center gap-1.5"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  <span>Prev</span>
                </button>
                <div className="text-xs text-slate-400 px-3">
                  Page <span className="font-semibold text-slate-200">{page}</span> of{' '}
                  <span className="font-semibold text-slate-200">{totalPages}</span>
                </div>
                <button
                  onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-xs inline-flex items-center gap-1.5"
                >
                  <span>Next</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Details Inspector Panel Drawer */}
      {selectedDevice && (
        <div className="fixed inset-0 z-40 flex justify-end bg-slate-950/65 backdrop-blur-sm transition-opacity duration-300">
          {/* Dismiss Back-Layer */}
          <div className="absolute inset-0" onClick={() => setSelectedDevice(null)} />

          <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl h-full flex flex-col justify-between z-10 animate-slide-in">
            <div>
              {/* Header */}
              <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-200 truncate">{selectedDevice.device_name}</h2>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">{selectedDevice.id}</p>
                </div>
                <button
                  onClick={() => setSelectedDevice(null)}
                  className="p-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-all"
                >
                  <X className="h-4.5 w-4.5" />
                </button>
              </div>

              {/* Data Rows */}
              <div className="p-6 space-y-6">
                <div>
                  <h4 className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-2">Device Information</h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center py-2 border-b border-slate-800/40">
                      <span className="text-xs text-slate-400">IP Address</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-200">{selectedDevice.ip_address}</span>
                        <button
                          onClick={() => copyToClipboard(selectedDevice.ip_address, 'IP Address')}
                          className="text-slate-500 hover:text-slate-300 transition-colors"
                          title="Copy IP"
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-800/40">
                      <span className="text-xs text-slate-400">Device Type</span>
                      <span className="text-xs uppercase px-2 py-0.5 rounded bg-slate-950 text-violet-400 border border-slate-800 font-semibold tracking-wide">
                        {selectedDevice.device_type}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-800/40">
                      <span className="text-xs text-slate-400">Current Status</span>
                      <span className={`text-xs uppercase px-2 py-0.5 rounded font-semibold ${getStatusBadge(selectedDevice.status).style}`}>
                        {selectedDevice.status}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-800/40">
                      <span className="text-xs text-slate-400">Physical Location</span>
                      <div className="flex items-center gap-1.5 text-slate-200 text-xs">
                        <MapPin className="h-3.5 w-3.5 text-slate-500" />
                        <span>{selectedDevice.location || 'Not Specified'}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs text-slate-500 font-bold uppercase tracking-wider mb-2">Audit Logs</h4>
                  <div className="space-y-3">
                    <div className="flex gap-3 text-xs p-3 bg-slate-950/40 border border-slate-800/50 rounded-xl">
                      <Clock className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-slate-400">Registered</p>
                        <p className="text-slate-500 mt-1">{new Date(selectedDevice.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="flex gap-3 text-xs p-3 bg-slate-950/40 border border-slate-800/50 rounded-xl">
                      <RefreshCw className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-slate-400">Last Telemetry State Synchronization</p>
                        <p className="text-slate-500 mt-1">{new Date(selectedDevice.updated_at).toLocaleString()}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Actions Drawer Panel */}
            {canWrite && (
              <div className="p-6 border-t border-slate-800 bg-slate-950/20 flex gap-3">
                <button
                  onClick={() => openModal('edit', selectedDevice)}
                  className="flex-1 inline-flex justify-center items-center gap-2 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 py-3 text-xs font-semibold text-slate-300 hover:text-slate-100 transition-all"
                >
                  <Edit2 className="h-4 w-4" />
                  <span>Modify Settings</span>
                </button>
                {canDelete && (
                  <button
                    onClick={() => setDeleteConfirm(selectedDevice)}
                    className="inline-flex justify-center items-center p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-white transition-all"
                  >
                    <Trash2 className="h-4.5 w-4.5" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add / Edit Form Modal Dialog */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800/80 rounded-2xl shadow-2xl overflow-hidden animate-slide-in">
            {/* Modal Title */}
            <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-200">
                {activeModal.mode === 'create' ? 'Register New Network Device' : 'Edit Device Settings'}
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="p-1 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition-all"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              {/* Fields */}
              <div className="p-6 space-y-4">
                {/* Device Name */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Device Hostname <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. cisco-router-01"
                    className={`w-full px-4 py-2.5 bg-slate-950/60 border ${
                      formErrors.name ? 'border-red-500' : 'border-slate-800 focus:border-violet-500/60'
                    } focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm placeholder-slate-600 outline-none transition-all`}
                  />
                  {formErrors.name && (
                    <p className="text-red-400 text-xs mt-1.5 font-medium">{formErrors.name}</p>
                  )}
                </div>

                {/* IP Address */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    IP Address <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formIp}
                    onChange={(e) => setFormIp(e.target.value)}
                    placeholder="e.g. 192.168.1.1 or 2001:db8::1"
                    className={`w-full px-4 py-2.5 bg-slate-950/60 border ${
                      formErrors.ip ? 'border-red-500' : 'border-slate-800 focus:border-violet-500/60'
                    } focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm placeholder-slate-600 outline-none transition-all`}
                  />
                  {formErrors.ip && (
                    <p className="text-red-400 text-xs mt-1.5 font-medium">{formErrors.ip}</p>
                  )}
                </div>

                {/* Device Type & Status Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                      Asset Type
                    </label>
                    <select
                      value={formType}
                      onChange={(e) => setFormType(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm text-slate-300 outline-none transition-all"
                    >
                      <option value="router">Router</option>
                      <option value="switch">Switch</option>
                      <option value="firewall">Firewall</option>
                      <option value="server">Server</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                      Operational Status
                    </label>
                    <select
                      value={formStatus}
                      onChange={(e) => setFormStatus(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm text-slate-300 outline-none transition-all"
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="maintenance">Maintenance</option>
                    </select>
                  </div>
                </div>

                {/* Location */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Physical Location
                  </label>
                  <input
                    type="text"
                    value={formLocation}
                    onChange={(e) => setFormLocation(e.target.value)}
                    placeholder="e.g. Phoenix-DC-Rack A3"
                    className="w-full px-4 py-2.5 bg-slate-950/60 border border-slate-800 focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/20 rounded-xl text-sm placeholder-slate-600 outline-none transition-all"
                  />
                </div>
              </div>

              {/* Form Buttons */}
              <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/40 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setActiveModal(null)}
                  className="px-4 py-2 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-sm text-slate-300 transition-all font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-sm text-white rounded-xl shadow-lg transition-all font-semibold active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Saving changes...' : 'Save Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Warning Modal (Admin only) */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-red-500/20 rounded-2xl shadow-2xl overflow-hidden animate-slide-in">
            <div className="p-6">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-500 mb-4">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <h3 className="text-center text-lg font-bold text-slate-100">Confirm Asset Decommission</h3>
              <p className="text-center text-xs text-slate-400 mt-2">
                Are you absolutely sure you want to decommission and delete device{' '}
                <span className="font-bold text-slate-200">{deleteConfirm.device_name}</span> ({deleteConfirm.ip_address})?
              </p>
              <div className="mt-3 p-2 bg-rose-500/5 border border-rose-500/10 rounded-xl text-center">
                <span className="text-[10px] text-rose-400 font-semibold uppercase tracking-wider">
                  Caution: This action cannot be undone and will purge audit histories.
                </span>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/40 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-semibold text-slate-300 transition-all"
              >
                Keep Device
              </button>
              <button
                type="button"
                onClick={handleDeleteSubmit}
                disabled={submitting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-xs font-semibold text-white rounded-xl shadow-lg transition-all active:scale-95 disabled:opacity-50"
              >
                {submitting ? 'Decommissioning...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating container for micro-animations notifications */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  );
};

export default Devices;
