/**
 * pages/Register.jsx
 * ==================
 * Operator Registration / Enrollment Page
 * 
 * WHY THIS FILE EXISTS:
 *     Enables enrollment of new network operations personnel with specific RBAC roles.
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, User, Mail, Shield, AlertCircle, CheckCircle } from 'lucide-react';

export const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role: 'operator',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.email || !formData.password) {
      setError('Please fill in all fields');
      return;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);
    try {
      await register(
        formData.username,
        formData.email,
        formData.password,
        formData.role
      );
      setSuccess(true);
      setError('');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 'Registration failed. Check network or credentials.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-slate-950 px-4 overflow-hidden">
      {/* Background ambient glow spots */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-96 w-96 rounded-full bg-violet-600/10 blur-[100px]" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-96 w-96 rounded-full bg-emerald-600/10 blur-[100px]" />

      <div className="w-full max-w-lg">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-500 text-white shadow-lg shadow-violet-500/20">
            <Shield className="h-8 w-8" />
          </div>
          <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            AETHER NOC
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Enroll New Operator Profile
          </p>
        </div>

        {/* Register Card */}
        <div className="glass-panel rounded-3xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-slate-100 mb-6">Create Operator Account</h2>

          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 p-4 border border-red-500/20 text-red-400 text-sm">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="mb-6 flex items-start gap-3 rounded-xl bg-emerald-500/10 p-4 border border-emerald-500/20 text-emerald-400 text-sm">
              <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <span>Enrolled successfully! Redirecting to credentials gate...</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username Input */}
            <div>
              <label htmlFor="username" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Username
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
                  disabled={loading || success}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20"
                />
              </div>
            </div>

            {/* Email Input */}
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Corporate Email
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                  <Mail className="h-5 w-5" />
                </div>
                <input
                  type="email"
                  name="email"
                  id="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="chief@aethernoc.net"
                  disabled={loading || success}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Secure Password
              </label>
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
                  placeholder="Min. 8 characters"
                  disabled={loading || success}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 placeholder-slate-500 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20"
                />
              </div>
            </div>

            {/* Role Select Input */}
            <div>
              <label htmlFor="role" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                NOC Role Scope
              </label>
              <div className="relative">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-slate-500">
                  <Shield className="h-5 w-5" />
                </div>
                <select
                  name="role"
                  id="role"
                  value={formData.role}
                  onChange={handleChange}
                  disabled={loading || success}
                  className="block w-full rounded-2xl border border-slate-800 bg-slate-900/60 py-3.5 pl-11 pr-4 text-slate-100 outline-none transition-all focus:border-violet-500 focus:bg-slate-900 focus:ring-2 focus:ring-violet-500/20 appearance-none cursor-pointer"
                >
                  <option value="operator">Operator (Normal operations read/write)</option>
                  <option value="admin">Administrator (Full write and delete controls)</option>
                  <option value="viewer">Viewer (Read-only reports)</option>
                </select>
                {/* Custom arrow icon for select */}
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-4 text-slate-500">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-4 w-4">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="relative flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3.5 text-sm font-semibold text-white shadow-lg transition-all hover:from-violet-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2 focus:ring-offset-slate-950 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                'Enroll Profile'
              )}
            </button>
          </form>

          {/* Login Redirect */}
          <div className="mt-8 text-center text-sm text-slate-400 border-t border-slate-800/40 pt-6">
            Already have credentials?{' '}
            <Link to="/login" className="font-semibold text-violet-400 hover:text-violet-300 hover:underline">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;
