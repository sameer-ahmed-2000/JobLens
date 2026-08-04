import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SparklesIcon, SettingsIcon, LogOutIcon, KeyIcon } from './icons';
import { SignupModal } from './SignupModal';
import { ProfileSettingsPanel } from './ProfileSettingsPanel';
import { getProfile } from '../services/api';
import { DEFAULT_USER_TOKEN } from '../constants/auth';
import type { UserProfile } from '../types';

export const Header: React.FC = () => {
  const queryClient = useQueryClient();

  const [token, setToken] = useState(() => {
    return localStorage.getItem('joblens_auth_token') || DEFAULT_USER_TOKEN;
  });

  const [isSignupOpen, setIsSignupOpen] = useState(false);
  const [modalInitialTab, setModalInitialTab] = useState<'signup' | 'signin'>('signup');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const hasCustomToken = !!token && token !== DEFAULT_USER_TOKEN;

  // Fetch User Profile if token exists
  const { data: userProfile, isError } = useQuery<UserProfile>({
    queryKey: ['userProfile', token],
    queryFn: getProfile,
    enabled: hasCustomToken,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Stale/Corrupted token auto-cleanup effect:
  // If getProfile fails with 401/403, purge the dead token and return to guest mode cleanly
  useEffect(() => {
    if (isError && hasCustomToken) {
      console.warn("Session token is dead or expired. Purging localStorage and resetting to guest mode.");
      localStorage.removeItem('joblens_auth_token');
      setToken(DEFAULT_USER_TOKEN);
      queryClient.invalidateQueries();
    }
  }, [isError, hasCustomToken, queryClient]);

  const handleSignupSuccess = (newToken: string) => {
    localStorage.setItem('joblens_auth_token', newToken);
    setToken(newToken);
    queryClient.invalidateQueries();
  };

  const handleSignOut = () => {
    localStorage.removeItem('joblens_auth_token');
    setToken(DEFAULT_USER_TOKEN);
    queryClient.clear();
    window.location.reload();
  };

  const openAuthModal = (tab: 'signup' | 'signin') => {
    setModalInitialTab(tab);
    setIsSignupOpen(true);
  };

  const getInitials = (name?: string, email?: string) => {
    if (name && name.trim()) {
      const parts = name.trim().split(/\s+/);
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return parts[0].slice(0, 2).toUpperCase();
    }
    if (email) return email.slice(0, 2).toUpperCase();
    return 'JL';
  };

  return (
    <header className="bg-surface border-b border-gray-850 sticky top-0 z-30 shadow-md font-body">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          
          {/* Branding & Tagline */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-base border border-gray-800 text-focus-confirm flex items-center justify-center shadow-inner">
              <SparklesIcon size={22} className="animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-text-warm font-display">
                  JobLens
                </h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-base border border-gray-800 text-focus-confirm">
                  AI Job Discovery
                </span>
              </div>
              <p className="text-[11px] text-gray-500 hidden sm:block font-mono">
                POWERED BY LANGGRAPH AGENTIC DISCOVERY & RAG GAP ANALYSIS
              </p>
            </div>
          </div>

          {/* Navigation & Auth Widgets */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            
            {hasCustomToken && userProfile ? (
              /* --- User Profile Badge & Actions (Authenticated) --- */
              <div className="flex items-center gap-2 bg-base p-1.5 rounded-2xl border border-gray-800 shadow-xs">
                
                {/* User Avatar & Name Chip */}
                <div className="flex items-center space-x-2.5 px-2.5 py-1">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-extrabold text-xs shadow-sm font-mono">
                    {getInitials(userProfile.name, userProfile.email)}
                  </div>
                  <div className="hidden md:block text-left">
                    <p className="text-xs font-bold text-text-warm leading-tight">{userProfile.name}</p>
                    <p className="text-[10px] text-gray-400 font-mono truncate max-w-[130px]">{userProfile.email}</p>
                  </div>
                </div>

                <div className="h-5 w-px bg-gray-800" />

                {/* Settings Button */}
                <button
                  onClick={() => setIsSettingsOpen(true)}
                  title="Profile Settings & Aperture Thresholds"
                  className="flex items-center gap-1 bg-surface/80 hover:bg-surface text-gray-300 hover:text-text-warm px-2.5 py-1.5 rounded-xl border border-gray-800 text-xs font-bold transition-all cursor-pointer"
                >
                  <SettingsIcon size={14} className="text-gray-400" />
                  <span className="hidden lg:inline font-mono">Settings</span>
                </button>

                {/* Sign Out Button */}
                <button
                  onClick={handleSignOut}
                  title="Sign out of JobLens session"
                  className="flex items-center gap-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer font-mono"
                >
                  <LogOutIcon size={14} />
                  <span>Sign Out</span>
                </button>

              </div>
            ) : (
              /* --- Guest Auth Controls (Signed Out) --- */
              <div className="flex items-center gap-2">
                
                {/* Sign In Button */}
                <button
                  onClick={() => openAuthModal('signin')}
                  className="flex items-center gap-1.5 bg-base hover:bg-surface border border-gray-800 text-gray-300 hover:text-text-warm px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer font-mono shadow-xs"
                >
                  <KeyIcon size={14} className="text-indigo-400" />
                  <span>Sign In</span>
                </button>

                {/* Sign Up Button */}
                <button
                  onClick={() => openAuthModal('signup')}
                  className="flex items-center gap-1.5 bg-focus-confirm/10 hover:bg-focus-confirm/25 border border-focus-confirm/30 text-focus-confirm px-4 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer font-mono shadow-xs"
                >
                  <SparklesIcon size={14} />
                  <span>Sign Up</span>
                </button>
              </div>
            )}

            {/* Main Navigation Tabs */}
            <div className="flex items-center space-x-1 bg-base p-1 rounded-xl border border-gray-850">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `px-3.5 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-colors font-mono ${
                    isActive
                      ? 'bg-surface text-focus-confirm shadow-sm border border-gray-800'
                      : 'text-gray-400 hover:text-text-warm hover:bg-surface/50'
                  }`
                }
              >
                Discovery
              </NavLink>
              <NavLink
                to="/workspace"
                className={({ isActive }) =>
                  `px-3.5 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-colors font-mono ${
                    isActive
                      ? 'bg-surface text-focus-confirm shadow-sm border border-gray-800'
                      : 'text-gray-400 hover:text-text-warm hover:bg-surface/50'
                  }`
                }
              >
                Workspace
              </NavLink>
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `px-3.5 py-1.5 text-xs sm:text-sm font-bold rounded-lg transition-colors font-mono ${
                    isActive
                      ? 'bg-surface text-focus-confirm shadow-sm border border-gray-800'
                      : 'text-gray-400 hover:text-text-warm hover:bg-surface/50'
                  }`
                }
              >
                Profile
              </NavLink>
            </div>

          </div>

        </div>
      </div>

      {/* Profile Settings Panel */}
      <ProfileSettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Sign Up / Sign In Modal */}
      <SignupModal
        isOpen={isSignupOpen}
        onClose={() => setIsSignupOpen(false)}
        onSuccess={handleSignupSuccess}
        initialTab={modalInitialTab}
      />
    </header>
  );
};
