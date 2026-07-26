import React, { useState } from 'react';
import { XIcon, SparklesIcon } from './icons';
import { signupUser } from '../services/api';
import type { SignupData } from '../services/api';
import type { UserProfile } from '../types';

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (token: string, user: UserProfile) => void;
}

export const SignupModal: React.FC<SignupModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [inviteCode, setInviteCode] = useState('joblens-beta-2026');
  const [whatsapp, setWhatsapp] = useState('');
  const [title, setTitle] = useState('Software Engineer');
  const [yearsExperience, setYearsExperience] = useState(3.0);
  const [skillsText, setSkillsText] = useState('Python, FastAPI, React, TypeScript');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [createdUser, setCreatedUser] = useState<UserProfile | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setIsSubmitting(true);

    const skills = skillsText
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    const payload: SignupData = {
      name: name.trim(),
      email: email.trim(),
      invite_code: inviteCode.trim(),
      whatsapp_number: whatsapp.trim() || undefined,
      title: title.trim(),
      years_experience: Number(yearsExperience),
      skills,
    };

    try {
      const res = await signupUser(payload);
      setIssuedToken(res.raw_token);
      setCreatedUser(res.user);
    } catch (err: any) {
      console.error("Signup error", err);
      const msg = err.response?.data?.detail || "Signup failed. Please verify your invite code and email.";
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopy = () => {
    if (issuedToken) {
      navigator.clipboard.writeText(issuedToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleUseToken = () => {
    if (issuedToken && createdUser) {
      onSuccess(issuedToken, createdUser);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-950/60 backdrop-blur-xs transition-opacity">
      <div className="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-gray-100 overflow-hidden p-6 space-y-6">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-gray-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center text-white shadow-sm">
              <SparklesIcon size={20} />
            </div>
            <div>
              <h3 className="text-xl font-extrabold text-gray-900">Self-Serve Signup</h3>
              <p className="text-xs text-gray-500">Create your JobLens account & initialize resume RAG profile</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
          >
            <XIcon size={18} />
          </button>
        </div>

        {issuedToken ? (
          /* Token Issued Screen */
          <div className="space-y-5 animate-fade-in">
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-center">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-2 text-xl font-bold">
                ✓
              </div>
              <h4 className="text-base font-bold text-emerald-900">Account Created Successfully!</h4>
              <p className="text-xs text-emerald-700 mt-1">
                Here is your secret API Access Key. <strong>Save it safely — it will not be shown again!</strong>
              </p>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Your API Token Key</label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={issuedToken}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-mono font-semibold text-gray-800 select-all focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs rounded-xl transition-colors shrink-0 cursor-pointer"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100 flex justify-end">
              <button
                type="button"
                onClick={handleUseToken}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer"
              >
                Use Token & Start Discovering Jobs →
              </button>
            </div>
          </div>
        ) : (
          /* Signup Form */
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Invite Token */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                Beta Invite Code <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                placeholder="joblens-beta-2026"
                className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {/* Name & Email Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Full Name <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Email <span className="text-red-500">*</span></label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@example.com"
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Target Role & Experience */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2 space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Target Job Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. AI Engineer, Full Stack Lead"
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Experience (Yrs)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={yearsExperience}
                  onChange={(e) => setYearsExperience(parseFloat(e.target.value) || 0)}
                  className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Skills */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                Key Skills <span className="text-[10px] text-gray-400 font-normal">(Comma-separated for RAG match)</span>
              </label>
              <input
                type="text"
                value={skillsText}
                onChange={(e) => setSkillsText(e.target.value)}
                placeholder="Python, LangChain, React, PostgreSQL"
                className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {/* WhatsApp (Optional) */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                WhatsApp Alert Number <span className="text-[10px] text-gray-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                value={whatsapp}
                onChange={(e) => setWhatsapp(e.target.value)}
                placeholder="+1234567890"
                className="w-full bg-white border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {errorMsg && (
              <div className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 p-2.5 rounded-lg leading-relaxed">
                {errorMsg}
              </div>
            )}

            {/* Submit & Cancel */}
            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-bold text-gray-500 hover:bg-gray-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm hover:shadow transition-all cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? 'Creating Account...' : 'Sign Up & Get Access Key'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
