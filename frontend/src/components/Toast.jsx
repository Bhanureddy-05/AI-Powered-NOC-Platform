/**
 * components/Toast.jsx
 * ====================
 * Premium Floating Toast Notification Component
 * 
 * WHY THIS FILE EXISTS:
 *     Provides instant user feedback for actions (e.g. "Device updated successfully",
 *     "Failed to register device: IP conflict"). Features fluid enter transitions.
 */

import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const Toast = ({ message, type = 'success', onClose, duration = 5000 }) => {
  useEffect(() => {
    if (duration) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const styles = {
    success: {
      bg: 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200',
      icon: <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />,
      glow: 'shadow-[0_0_20px_rgba(16,185,129,0.1)]',
    },
    error: {
      bg: 'bg-rose-950/90 border-rose-500/30 text-rose-200',
      icon: <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />,
      glow: 'shadow-[0_0_20px_rgba(244,63,94,0.1)]',
    },
    info: {
      bg: 'bg-blue-950/90 border-blue-500/30 text-blue-200',
      icon: <Info className="h-5 w-5 text-blue-400 shrink-0" />,
      glow: 'shadow-[0_0_20px_rgba(59,130,246,0.1)]',
    },
  };

  const currentStyle = styles[type] || styles.info;

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md transition-all duration-300 animate-slide-in ${currentStyle.bg} ${currentStyle.glow}`}
      role="alert"
    >
      {currentStyle.icon}
      <span className="text-sm font-medium">{message}</span>
      <button
        onClick={onClose}
        className="text-slate-400 hover:text-slate-200 transition-colors ml-2 shrink-0"
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

export const ToastContainer = ({ toasts, removeToast }) => {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-md w-full sm:w-auto">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
};

export default ToastContainer;
