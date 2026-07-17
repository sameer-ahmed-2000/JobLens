import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { SparklesIcon, SettingsIcon, XIcon } from './icons';
import { getProfile, updateProfile } from '../services/api';
import type { UserProfile } from '../types';

export const Header: React.FC = () => {
  const [token, setToken] = useState(() => {
    return sessionStorage.getItem('joblens_auth_token') || 'default-user-token';
  });
  const [isEditing, setIsEditing] = useState(false);
  const [tempToken, setTempToken] = useState(token);

  // Settings profile states
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [notifyThreshold, setNotifyThreshold] = useState(0.85);
  const [displayThreshold, setDisplayThreshold] = useState(0.70);
  const [validationError, setValidationError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveToken = () => {
    const trimmed = tempToken.trim();
    if (trimmed) {
      sessionStorage.setItem('joblens_auth_token', trimmed);
      setToken(trimmed);
      setIsEditing(false);
      window.location.reload();
    }
  };

  const handleOpenSettings = async () => {
    setIsSettingsOpen(true);
    setValidationError('');
    setSaveSuccess(false);
    try {
      const data = await getProfile();
      setName(data.name);
      setEmail(data.email);
      setWhatsapp(data.whatsapp_number || '');
      setNotifyThreshold(data.notify_threshold);
      setDisplayThreshold(data.display_threshold);
    } catch (err) {
      console.error("Failed to load profile", err);
      setValidationError("Failed to load user profile settings.");
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');
    setSaveSuccess(false);
    
    if (notifyThreshold < displayThreshold) {
      setValidationError("Notification Threshold cannot be lower than Display Threshold. (Display Threshold determines which jobs are shown, while Notification Threshold determines which top matches trigger email/WhatsApp alerts).");
      return;
    }
    
    setIsSaving(true);
    try {
      await updateProfile({
        name,
        email,
        whatsapp_number: whatsapp.trim() || undefined,
        notify_threshold: notifyThreshold,
        display_threshold: displayThreshold
      });
      setSaveSuccess(true);
      setTimeout(() => {
        setIsSettingsOpen(false);
      }, 1500);
    } catch (err: any) {
      console.error("Failed to update profile", err);
      const msg = err.response?.data?.detail || "Failed to update profile settings.";
      setValidationError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          
          {/* Branding & SaaS Tagline */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center text-white shadow-sm">
              <SparklesIcon size={22} className="animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-gray-900">
                  JobLens
                </h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  AI Job Discovery
                </span>
              </div>
              <p className="text-xs text-gray-500 hidden sm:block">
                Powered by LangGraph Agentic Discovery & RAG Gap Analysis
              </p>
            </div>
          </div>

          {/* Navigation & Auth Widgets */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            
            {/* Auth token controller */}
            <div className="flex items-center space-x-2 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-200 text-xs">
              <span className="text-gray-400 font-medium">🔑 Key:</span>
              {isEditing ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="password"
                    value={tempToken}
                    onChange={(e) => setTempToken(e.target.value)}
                    placeholder="Enter API token"
                    className="w-32 bg-white border border-gray-300 rounded px-1.5 py-0.5 font-mono text-[11px] focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveToken();
                      if (e.key === 'Escape') {
                        setTempToken(token);
                        setIsEditing(false);
                      }
                    }}
                  />
                  <button
                    onClick={handleSaveToken}
                    className="bg-indigo-600 text-white font-bold px-2 py-0.5 rounded hover:bg-indigo-700 transition-colors cursor-pointer"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setTempToken(token);
                      setIsEditing(false);
                    }}
                    className="text-gray-500 hover:text-gray-700 transition-colors font-medium cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="font-mono text-gray-700 font-semibold max-w-[120px] truncate">
                    {token === 'default-user-token' ? 'default-user-token' : `${token.slice(0, 4)}...${token.slice(-4)}`}
                  </span>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="text-indigo-600 hover:text-indigo-800 font-bold hover:underline cursor-pointer"
                  >
                    Change
                  </button>
                </div>
              )}
            </div>

            {/* Settings button */}
            <button
              onClick={handleOpenSettings}
              className="flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-200 text-xs font-bold text-gray-700 hover:bg-gray-100 hover:text-indigo-700 transition-all cursor-pointer shadow-xs"
            >
              <SettingsIcon size={14} className="text-gray-500 hover:rotate-45 transition-transform" />
              <span>Settings</span>
            </button>

            {/* Navigation Tabs */}
            <div className="flex items-center space-x-1 bg-gray-50 p-1 rounded-xl border border-gray-200">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `px-4 py-1.5 text-sm font-bold rounded-lg transition-colors ${
                    isActive
                      ? 'bg-white text-indigo-700 shadow-sm border border-gray-200/60'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                  }`
                }
              >
                Discovery
              </NavLink>
              <NavLink
                to="/workspace"
                className={({ isActive }) =>
                  `px-4 py-1.5 text-sm font-bold rounded-lg transition-colors ${
                    isActive
                      ? 'bg-white text-indigo-700 shadow-sm border border-gray-200/60'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                  }`
                }
              >
                Workspace
              </NavLink>
            </div>

          </div>

        </div>
      </div>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-950/60 backdrop-blur-xs transition-opacity">
          <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-gray-100 overflow-hidden p-6 space-y-6">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
                  <SettingsIcon size={20} className="animate-spin-slow" />
                </div>
                <div>
                  <h3 className="text-lg font-extrabold text-gray-900">Notification Settings</h3>
                  <p className="text-xs text-gray-500">Manage thresholds and notification destinations</p>
                </div>
              </div>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
              >
                <XIcon size={18} />
              </button>
            </div>

            {/* Modal Content */}
            <form onSubmit={handleSaveSettings} className="space-y-4">
              
              {/* Name */}
              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Profile Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="Demo User"
                />
              </div>

              {/* Email */}
              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="user@joblens.ai"
                />
              </div>

              {/* WhatsApp Number */}
              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                  WhatsApp Number <span className="text-[10px] text-gray-400 font-normal">(Optional, starts with country code)</span>
                </label>
                <input
                  type="text"
                  value={whatsapp}
                  onChange={(e) => setWhatsapp(e.target.value)}
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  placeholder="+1234567890"
                />
                <p className="text-[10px] text-gray-400 leading-tight">
                  If set, alerts will default to WhatsApp Business API. If empty, defaults to email.
                </p>
              </div>

              {/* Threshold Fields */}
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Display Floor</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    required
                    value={displayThreshold}
                    onChange={(e) => setDisplayThreshold(parseFloat(e.target.value))}
                    className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                  <p className="text-[10px] text-gray-400">Score to show in list (e.g. 0.70)</p>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Notify Floor</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    required
                    value={notifyThreshold}
                    onChange={(e) => setNotifyThreshold(parseFloat(e.target.value))}
                    className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                  <p className="text-[10px] text-gray-400">Score to trigger alert (e.g. 0.85)</p>
                </div>
              </div>

              {/* Informative Help Text */}
              <p className="text-[11px] bg-gray-50 border border-gray-150 p-2.5 rounded-lg text-gray-500 leading-relaxed font-medium">
                ⚠️ <strong>Constraint:</strong> Notify floor must be greater than or equal to Display floor. JobLens must display a match before it can send you an alert.
              </p>

              {/* Errors & Success Feedback */}
              {validationError && (
                <div className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 p-2.5 rounded-lg leading-relaxed">
                  {validationError}
                </div>
              )}
              {saveSuccess && (
                <div className="text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg">
                  Settings saved successfully!
                </div>
              )}

              {/* Form Buttons */}
              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-bold text-gray-500 hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all hover:shadow-md cursor-pointer disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </header>
  );
};

