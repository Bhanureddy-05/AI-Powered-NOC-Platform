/**
 * components/ProtectedRoute.jsx
 * =============================
 * Secure Client-Side Route Shield
 * 
 * WHY THIS FILE EXISTS:
 *     We must prevent unauthenticated users from seeing the operational dashboard.
 *     This component wraps nested page paths, validating both login state
 *     and role authorizations (RBAC) before rendering content.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, user, loading } = useAuth();
  const location = useLocation();

  // 1. Show a loading screen during initial session check
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-violet-500 border-t-transparent"></div>
          <p className="text-sm font-medium text-slate-400">Verifying session...</p>
        </div>
      </div>
    );
  }

  // 2. Redirect to login if user is not authenticated
  if (!isAuthenticated) {
    // Save current path to return user here after successful login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 3. Enforce Role-Based Access Control (RBAC) if roles are specified
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 px-4">
        <div className="glass-panel max-w-md rounded-2xl p-8 text-center shadow-xl">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10 text-red-500">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-7 w-7">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.036h.008v.008H12v-.008z" />
            </svg>
          </div>
          <h1 className="mt-5 text-2xl font-bold text-slate-100">Access Denied</h1>
          <p className="mt-2 text-sm text-slate-400">
            Your current role <span className="font-semibold text-violet-400">({user.role})</span> does not have privileges to view this section.
          </p>
          <button
            onClick={() => window.history.back()}
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg transition-all hover:bg-violet-500 hover:shadow-violet-600/20 active:scale-95"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // 4. Render protected components if checks pass
  return children;
};

export default ProtectedRoute;
