/**
 * pages/Login.jsx
 * ===============
 * Premium NOC Platform Login Page
 * 
 * WHY THIS FILE EXISTS:
 *     Provides the entry screen for operators. Integrates AuthContext to process
 *     credentials and handles navigation.
 */

import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, User, AlertCircle, ShieldAlert } from 'lucide-react';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect to original page requested before interception, or default to Dashboard
  const from = location.state?.from?.pathname || '/';

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError(''); // Clear error on edit
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.password) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    try {
      await login(formData.username, formData.password);
      navigate(from, { replace: true });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Incorrect credentials or connection error'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-950 px-4 overflow-hidden">
      {/* Background abstract ambient glow spots */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-96 w-96 rounded-full bg-violet-600/10 blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-96 w-96 rounded-full bg-emerald-600/10 blur-[100px]" />

      <div className="w-full max-w-lg">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 text-white shadow-lg shadow-violet-500/20">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            AETHER NOC
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            AI-Powered Predictive Network Operations Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-panel rounded-3xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-slate-100 mb-6">Sign In to Dashboard</h2>

          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 p-4 border border-red-500/20 text-red-400 text-sm">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username/Email Input */}
            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Username or Email
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                  <User className="h-5 w-5" />
                </div>
                <input
                  type="text"
                  name="username"
                  id="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="operator_chief"
                  disabled={loading}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="password" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Password
                </label>
              </div>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                  <Lock className="h-5 w-5" />
                </div>
                <input
                  type="password"
                  name="password"
                  id="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  disabled={loading}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="relative flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3.5 text-sm font-semibold text-white shadow-lg transition-all hover:from-violet-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 focus:ring-offset-slate-950 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                'Access Control Center'
              )}
            </button>
          </form>

          {/* Registration Redirect */}
          <div className="mt-8 text-center text-sm text-slate-400 border-t border-slate-800/40 pt-6">
            New operator on shift?{' '}
            <Link to="/register" className="font-semibold text-violet-400 hover:text-violet-300 hover:underline">
              Request credentials
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
