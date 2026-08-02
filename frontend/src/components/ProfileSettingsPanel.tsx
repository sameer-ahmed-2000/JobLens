import React, { useState, useEffect } from 'react';
import { SettingsIcon, XIcon } from './icons';
import { ApertureDialControl } from './ApertureDialControl';
import { ResumeUploader } from './ResumeUploader';
import { getProfile, updateProfile, getLatestResumeStatus, getActiveResume } from '../services/api';
import type { ResumeFile, ActiveResume } from '../services/api';

interface ProfileSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ProfileSettingsPanel: React.FC<ProfileSettingsPanelProps> = ({ isOpen, onClose }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [notifyThreshold, setNotifyThreshold] = useState(0.85);
  const [displayThreshold, setDisplayThreshold] = useState(0.70);
  const [validationError, setValidationError] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [resumeFile, setResumeFile] = useState<ResumeFile | null>(null);
  const [activeResume, setActiveResume] = useState<ActiveResume | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    setValidationError('');
    setSaveSuccess(false);

    getProfile()
      .then((data) => {
        setName(data.name);
        setEmail(data.email);
        setWhatsapp(data.whatsapp_number || '');
        setNotifyThreshold(data.notify_threshold);
        setDisplayThreshold(data.display_threshold);
      })
      .catch((err) => {
        console.error('Failed to load profile', err);
        setValidationError('Failed to load user profile settings.');
      });

    getLatestResumeStatus()
      .then(setResumeFile)
      .catch((err) => console.error('Failed to load resume status', err));

    getActiveResume()
      .then(setActiveResume)
      .catch((err) => console.error('Failed to load active resume profile', err));
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError('');
    setSaveSuccess(false);

    if (notifyThreshold < displayThreshold) {
      setValidationError(
        'Notification Threshold cannot be lower than Display Threshold. (Display Threshold determines which jobs are shown, while Notification Threshold determines which top matches trigger email/WhatsApp alerts).'
      );
      return;
    }

    setIsSaving(true);
    try {
      await updateProfile({
        name,
        email,
        whatsapp_number: whatsapp.trim() || undefined,
        notify_threshold: notifyThreshold,
        display_threshold: displayThreshold,
      });
      setSaveSuccess(true);
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      console.error('Failed to update profile', err);
      const msg = err.response?.data?.detail || 'Failed to update profile settings.';
      setValidationError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base/80 backdrop-blur-md transition-opacity">
      <div className="bg-surface rounded-3xl max-w-md w-full shadow-2xl border border-gray-800 overflow-hidden p-6 space-y-6 text-text-warm font-body max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-gray-850 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-base text-focus-confirm border border-gray-850 rounded-xl">
              <SettingsIcon size={20} className="animate-spin-slow" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-text-warm font-display">Notification Settings</h3>
              <p className="text-xs text-gray-400 font-mono">Manage thresholds and notification destinations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-text-warm p-1 hover:bg-base rounded-lg transition-colors cursor-pointer"
          >
            <XIcon size={18} />
          </button>
        </div>

        {/* Modal Content */}
        <form onSubmit={handleSaveSettings} className="space-y-4">
          {/* Name */}
          <div className="space-y-1">
            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider font-mono">Profile Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-base border border-gray-800 text-text-warm rounded-xl px-3 py-2 text-sm focus:border-focus-confirm focus:ring-1 focus:ring-focus-confirm focus:outline-none"
              placeholder="Demo User"
            />
          </div>

          {/* Email */}
          <div className="space-y-1">
            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider font-mono">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-base border border-gray-800 text-text-warm rounded-xl px-3 py-2 text-sm focus:border-focus-confirm focus:ring-1 focus:ring-focus-confirm focus:outline-none"
              placeholder="user@joblens.ai"
            />
          </div>

          {/* WhatsApp Number */}
          <div className="space-y-1">
            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider font-mono">
              WhatsApp Number <span className="text-[10px] text-gray-500 font-normal">(Optional, starts with country code)</span>
            </label>
            <input
              type="text"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              className="w-full bg-base border border-gray-800 text-text-warm rounded-xl px-3 py-2 text-sm focus:border-focus-confirm focus:ring-1 focus:ring-focus-confirm focus:outline-none"
              placeholder="+1234567890"
            />
            <p className="text-[10px] text-gray-500 leading-tight font-mono">
              If set, alerts will default to WhatsApp Business API. If empty, defaults to email.
            </p>
          </div>

          {/* Resume Document Upload & Overview */}
          <ResumeUploader
            resumeFile={resumeFile}
            setResumeFile={setResumeFile}
            activeResume={activeResume}
            setActiveResume={setActiveResume}
          />

          {/* Circular Aperture Dial Settings Control */}
          <div className="space-y-2 pt-2">
            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider font-mono">
              Aperture Range Thresholds (f / display & notify)
            </label>
            <ApertureDialControl
              displayFloor={displayThreshold}
              notifyFloor={notifyThreshold}
              onChange={(displayVal, notifyVal) => {
                setDisplayThreshold(displayVal);
                setNotifyThreshold(notifyVal);
              }}
            />
          </div>

          {/* Informative Help Text */}
          <p className="text-[10px] bg-base border border-gray-850 p-2.5 rounded-lg text-gray-400 leading-relaxed font-mono">
            ⚠️ <strong>Constraint:</strong> Notify floor must be &gt;= Display floor. JobLens filters displaying matches before initiating notify sweeps.
          </p>

          {/* Errors & Success Feedback */}
          {validationError && (
            <div className="text-xs font-semibold text-alert-red bg-alert-red/10 border border-alert-red/20 p-2.5 rounded-lg leading-relaxed font-mono">
              {validationError}
            </div>
          )}
          {saveSuccess && (
            <div className="text-xs font-semibold text-focus-confirm bg-focus-confirm/10 border border-focus-confirm/20 p-2.5 rounded-lg font-mono">
              Settings saved successfully!
            </div>
          )}

          {/* Form Buttons */}
          <div className="flex items-center justify-end space-x-2 pt-4 border-t border-gray-850 font-mono">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-850 rounded-xl text-xs font-bold text-gray-400 hover:bg-base cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 bg-focus-confirm hover:bg-focus-confirm/90 text-[#1A1917] rounded-xl text-xs font-bold shadow-sm transition-all hover:shadow-md cursor-pointer disabled:opacity-50"
            >
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
