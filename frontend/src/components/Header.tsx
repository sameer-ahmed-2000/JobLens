import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { SparklesIcon, SettingsIcon } from './icons';
import { SignupModal } from './SignupModal';
import { TokenSettings } from './TokenSettings';
import { ProfileSettingsPanel } from './ProfileSettingsPanel';
import { DEFAULT_USER_TOKEN } from '../constants/auth';

export const Header: React.FC = () => {
  const [token, setToken] = useState(() => {
    return sessionStorage.getItem('joblens_auth_token') || DEFAULT_USER_TOKEN;
  });
  const [isSignupOpen, setIsSignupOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const handleSaveToken = (newToken: string) => {
    sessionStorage.setItem('joblens_auth_token', newToken);
    setToken(newToken);
    window.location.reload();
  };

  const handleSignupSuccess = (newToken: string) => {
    sessionStorage.setItem('joblens_auth_token', newToken);
    setToken(newToken);
    window.location.reload();
  };

  return (
    <header className="bg-surface border-b border-gray-850 sticky top-0 z-30 shadow-md font-body">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          
          {/* Branding & SaaS Tagline */}
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
            
            {/* Auth token controller widget */}
            <TokenSettings token={token} onSaveToken={handleSaveToken} />

            {/* Sign Up button */}
            <button
              onClick={() => setIsSignupOpen(true)}
              className="flex items-center gap-1.5 bg-focus-confirm/10 hover:bg-focus-confirm/25 border border-focus-confirm/20 text-focus-confirm px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
            >
              <SparklesIcon size={14} />
              <span>Sign Up</span>
            </button>

            {/* Settings button */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center gap-2 bg-base px-3 py-1.5 rounded-xl border border-gray-800 text-xs font-bold text-gray-300 hover:bg-surface hover:text-text-warm transition-all cursor-pointer shadow-xs"
            >
              <SettingsIcon size={14} className="text-gray-500 hover:rotate-45 transition-transform" />
              <span>Settings</span>
            </button>

            {/* Navigation Tabs */}
            <div className="flex items-center space-x-1 bg-base p-1 rounded-xl border border-gray-850">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `px-4 py-1.5 text-sm font-bold rounded-lg transition-colors font-mono ${
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
                  `px-4 py-1.5 text-sm font-bold rounded-lg transition-colors font-mono ${
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
                  `px-4 py-1.5 text-sm font-bold rounded-lg transition-colors font-mono ${
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

      {/* Settings Modal */}
      <ProfileSettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Signup Modal */}
      <SignupModal
        isOpen={isSignupOpen}
        onClose={() => setIsSignupOpen(false)}
        onSuccess={handleSignupSuccess}
      />
    </header>
  );
};
