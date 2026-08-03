import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { XIcon, SparklesIcon, CopyIcon, DownloadIcon, KeyIcon } from './icons';
import { signupUser, signinUser, uploadResume } from '../services/api';
import type { SignupData } from '../services/api';
import type { UserProfile } from '../types';

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (token: string, user: UserProfile) => void;
  initialTab?: 'signup' | 'signin';
}

export const SignupModal: React.FC<SignupModalProps> = ({ 
  isOpen, 
  onClose, 
  onSuccess,
  initialTab = 'signup' 
}) => {
  const [activeTab, setActiveTab] = useState<'signup' | 'signin'>(initialTab);

  // Signup fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('joblens-beta-2026');
  const [whatsapp, setWhatsapp] = useState('');
  const [title, setTitle] = useState('Software Engineer');
  const [yearsExperience, setYearsExperience] = useState(3.0);
  const [skillsText, setSkillsText] = useState('Python, FastAPI, React, TypeScript');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Signin fields
  const [signinEmail, setSigninEmail] = useState('');
  const [signinPassword, setSigninPassword] = useState('');

  // Status & Key Backup screen
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [createdUser, setCreatedUser] = useState<UserProfile | null>(null);
  const [copied, setCopied] = useState(false);
  const [showMaskedToken, setShowMaskedToken] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      setErrorMsg('');
      setIsSubmitting(false);
      setIssuedToken(null);
      setCreatedUser(null);
      setResumeFile(null);
      setSigninEmail('');
      setSigninPassword('');
      setPassword('');
    }
  }, [isOpen, initialTab]);

  if (!isOpen) return null;

  // --- Sign Up Submission ---
  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!resumeFile) {
      setErrorMsg('Uploading your resume (.pdf or .docx) is compulsory for account creation.');
      return;
    }

    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);

    const skills = skillsText
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    const payload: SignupData = {
      name: name.trim(),
      email: email.trim(),
      password: password,
      invite_code: inviteCode.trim(),
      whatsapp_number: whatsapp.trim() || undefined,
      title: title.trim(),
      years_experience: Number(yearsExperience),
      skills,
    };

    try {
      // 1. Create User Account
      const res = await signupUser(payload);
      const token = res.raw_token;

      // 2. Automatically store token in sessionStorage for immediate current-tab login
      sessionStorage.setItem('joblens_auth_token', token);

      // 3. Upload Resume asynchronously (202 Accepted, non-blocking SSE)
      try {
        await uploadResume(resumeFile);
      } catch (uploadErr: any) {
        console.error("Resume upload initial error:", uploadErr);
        // Non-blocking error -- user profile still created
      }

      setIssuedToken(token);
      setCreatedUser(res.user);
      onSuccess(token, res.user);
    } catch (err: any) {
      console.error("Signup error", err);
      const msg = err.response?.data?.detail || "Signup failed. Please verify your invite code and email.";
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Sign In Submission ---
  const handleSigninSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    
    if (!signinEmail.trim() || !signinPassword) {
      setErrorMsg('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await signinUser({ email: signinEmail.trim(), password: signinPassword });
      
      // Token is valid! Store in sessionStorage and sign in.
      sessionStorage.setItem('joblens_auth_token', res.raw_token);
      onSuccess(res.raw_token, res.user);
      onClose();
    } catch (err: any) {
      console.error("Sign-in validation failed:", err);
      const msg = err.response?.data?.detail || "Invalid email or password. Please try again.";
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Backup Handlers ---
  const handleCopyToken = () => {
    if (issuedToken) {
      navigator.clipboard.writeText(issuedToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadBackup = () => {
    if (!issuedToken) return;
    const content = `=====================================================
JOBLENS AI - ACCESS KEY BACKUP
=====================================================
User: ${createdUser?.name || 'User'} (${createdUser?.email || ''})
Date: ${new Date().toISOString()}

Access Key: ${issuedToken}

IMPORTANT: Keep this key safe! You will need it to sign in to JobLens
from other browsers, devices, or after clearing browser data.
=====================================================`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `joblens-key-backup.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'pdf' && ext !== 'docx') {
        setErrorMsg('Invalid file format. Only .pdf and .docx files are accepted.');
        setResumeFile(null);
        return;
      }
      setErrorMsg('');
      setResumeFile(file);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-950/60 backdrop-blur-xs transition-opacity">
      <div className="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-gray-100 overflow-hidden p-6 space-y-6 max-h-[90vh] overflow-y-auto">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-gray-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-500 flex items-center justify-center text-white shadow-sm">
              <SparklesIcon size={20} />
            </div>
            <div>
              <h3 className="text-xl font-extrabold text-gray-900">JobLens Account Access</h3>
              <p className="text-xs text-gray-500">Self-serve signup & resume RAG profile initialization</p>
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
          /* One-Time Secret Key Backup Screen */
          <div className="space-y-5 animate-fade-in">
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-center">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-2 text-xl font-bold">
                ✓
              </div>
              <h4 className="text-base font-bold text-emerald-900">Account & RAG Profile Created!</h4>
              <p className="text-xs text-emerald-700 mt-1 leading-relaxed">
                You are now logged in! Save your secret Access Key below so you can sign in again from other devices or browsers.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Your API Access Key</label>
                <button
                  type="button"
                  onClick={() => setShowMaskedToken(!showMaskedToken)}
                  className="text-[11px] text-indigo-600 hover:underline font-semibold cursor-pointer"
                >
                  {showMaskedToken ? 'Show Key' : 'Mask Key'}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type={showMaskedToken ? 'password' : 'text'}
                  readOnly
                  value={issuedToken}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-xs font-mono font-semibold text-gray-800 select-all focus:outline-none"
                />
              </div>

              {/* Copy & Download Backup Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleCopyToken}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-gray-100 hover:bg-gray-200 text-gray-800 font-bold text-xs rounded-xl transition-colors cursor-pointer border border-gray-200"
                >
                  <CopyIcon size={14} />
                  <span>{copied ? 'Copied to Clipboard!' : 'Copy Key'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownloadBackup}
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-xs rounded-xl transition-colors cursor-pointer border border-indigo-200"
                >
                  <DownloadIcon size={14} />
                  <span>Download Backup (.txt)</span>
                </button>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100">
              <button
                type="button"
                onClick={onClose}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer"
              >
                Start Discovering Jobs →
              </button>
            </div>
          </div>
        ) : (
          /* Sign Up / Sign In Tab Switcher & Forms */
          <div className="space-y-4">
            
            {/* Tab Navigation */}
            <div className="flex bg-gray-100 p-1 rounded-xl border border-gray-200">
              <button
                type="button"
                onClick={() => { setActiveTab('signup'); setErrorMsg(''); }}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  activeTab === 'signup' 
                    ? 'bg-white text-indigo-600 shadow-xs' 
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                Create Account (Sign Up)
              </button>
              <button
                type="button"
                onClick={() => { setActiveTab('signin'); setErrorMsg(''); }}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                  activeTab === 'signin' 
                    ? 'bg-white text-indigo-600 shadow-xs' 
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                Sign In with Email
              </button>
            </div>

            {activeTab === 'signup' ? (
              /* --- SIGN UP FORM --- */
              <form onSubmit={handleSignupSubmit} className="space-y-4">
                
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
                    className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
                      className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
                      className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                {/* Password Grid */}
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Password <span className="text-red-500">*</span></label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min 8 characters"
                    className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
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
                      className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
                      className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
                    className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                {/* COMPULSORY Resume File Upload Dropzone */}
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                    Resume Document <span className="text-red-500">* (Compulsory PDF/DOCX)</span>
                  </label>
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDragOver(false);
                      const file = e.dataTransfer.files?.[0];
                      if (file) {
                        const ext = file.name.split('.').pop()?.toLowerCase();
                        if (ext === 'pdf' || ext === 'docx') {
                          setErrorMsg('');
                          setResumeFile(file);
                        } else {
                          setErrorMsg('Invalid file format. Only .pdf and .docx files are accepted.');
                        }
                      }
                    }}
                    className={`relative border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all ${
                      resumeFile 
                        ? 'border-emerald-500 bg-emerald-50/50' 
                        : dragOver 
                        ? 'border-indigo-500 bg-indigo-50/50' 
                        : 'border-gray-200 hover:border-indigo-400 bg-gray-50/50'
                    }`}
                  >
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      onChange={handleFileChange}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    {resumeFile ? (
                      <div className="flex items-center justify-between px-2">
                        <div className="flex items-center space-x-2 text-left">
                          <span className="text-xl">📄</span>
                          <div>
                            <p className="text-xs font-bold text-emerald-900 truncate max-w-[220px]">{resumeFile.name}</p>
                            <p className="text-[10px] text-emerald-700">{(resumeFile.size / 1024).toFixed(1)} KB • Ready for RAG Indexing</p>
                          </div>
                        </div>
                        <span className="text-xs font-bold text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-md">Attached</span>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div className="text-lg">📤</div>
                        <p className="text-xs font-bold text-gray-700">Click or drag resume file here (.pdf or .docx)</p>
                        <p className="text-[10px] text-gray-400">Required to initialize your AI Job Matching profile</p>
                      </div>
                    )}
                  </div>
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
                    className="w-full bg-white border border-gray-200 text-black rounded-xl px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
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
                    {isSubmitting ? 'Creating Account & Resume Profile...' : 'Sign Up & Get Access Key'}
                  </button>
                </div>
              </form>
            ) : (
              /* --- SIGN IN FORM --- */
              <form onSubmit={handleSigninSubmit} className="space-y-4 pt-2">
                <div className="bg-indigo-50/60 border border-indigo-100 rounded-2xl p-4 text-xs text-indigo-900 space-y-1">
                  <div className="flex items-center space-x-2 font-bold">
                    <KeyIcon size={16} className="text-indigo-600" />
                    <span>Existing User Sign In</span>
                  </div>
                  <p className="text-[11px] text-indigo-700 leading-relaxed">
                    Enter your email and password to securely log into your JobLens account.
                  </p>
                </div>

                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Email</label>
                    <input
                      type="email"
                      required
                      value={signinEmail}
                      onChange={(e) => setSigninEmail(e.target.value)}
                      placeholder="alex@example.com"
                      className="w-full bg-white border border-gray-200 text-black rounded-xl p-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Password</label>
                    <input
                      type="password"
                      required
                      value={signinPassword}
                      onChange={(e) => setSigninPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-white border border-gray-200 text-black rounded-xl p-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>

                {errorMsg && (
                  <div className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 p-2.5 rounded-lg leading-relaxed">
                    {errorMsg}
                  </div>
                )}

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
                    {isSubmitting ? 'Signing In...' : 'Sign In'}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
