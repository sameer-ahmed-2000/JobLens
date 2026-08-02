import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  getLatestResumeStatus, 
  getActiveResume, 
  uploadResume, 
  reprocessResume, 
  getResumeDownloadUrl, 
  createStreamTicket,
  QUERY_CONFIG 
} from '../services/api';
import type { ResumeFile, ActiveResume } from '../services/api';


export const CareerProfile: React.FC = () => {
  const queryClient = useQueryClient();
  const [uploadProgress, setUploadProgress] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'failed'>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [showRawText, setShowRawText] = useState(false);
  const [skillSearch, setSkillSearch] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' | 'error' } | null>(null);

  // Queries for status & active profile
  const { data: latestFile, refetch: refetchStatus } = useQuery<ResumeFile | null>({
    queryKey: ['resumeStatus'],
    queryFn: getLatestResumeStatus,
    ...QUERY_CONFIG,
  });

  const { data: activeResume, refetch: refetchActive } = useQuery<ActiveResume | null>({
    queryKey: ['activeResume'],
    queryFn: getActiveResume,
    ...QUERY_CONFIG,
  });

  // Watch status changes to map uploadProgress
  useEffect(() => {
    if (latestFile) {
      if (latestFile.processing_status === 'pending' || latestFile.processing_status === 'processing') {
        setUploadProgress('processing');
      } else if (latestFile.processing_status === 'complete') {
        setUploadProgress('complete');
      } else if (latestFile.processing_status === 'failed') {
        setUploadProgress('failed');
        setUploadError(latestFile.error_message);
      }
    } else {
      setUploadProgress('idle');
    }
  }, [latestFile]);

  // Real-time SSE Handler
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let isActive = true;

    const setupSSE = async () => {
      try {
        const ticket = await createStreamTicket();
        if (!isActive) return;

        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        eventSource = new EventSource(`${API_URL}/api/stream/jobs?ticket=${ticket}`);

        eventSource.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'resume_processed') {
              refetchStatus();
              refetchActive();
              queryClient.invalidateQueries({ queryKey: ['postings'] });

              if (payload.status === 'complete') {
                showToast(`Resume parsed successfully!`, 'success');
                setUploadProgress('complete');
              } else if (payload.status === 'failed') {
                showToast(`Resume parsing failed: ${payload.error_message || 'Format error'}`, 'error');
                setUploadProgress('failed');
                setUploadError(payload.error_message || 'Format validation failed.');
              }
            }
          } catch (err) {
            console.error("Failed to parse SSE payload", err);
          }
        };
      } catch (err) {
        console.error("SSE Connection Ticket failure in Profile", err);
      }
    };

    setupSSE();

    return () => {
      isActive = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [refetchStatus, refetchActive, queryClient]);

  const showToast = (message: string, type: 'success' | 'info' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const handleUpload = async (file: File) => {
    if (!file) return;
    setUploadProgress('uploading');
    setUploadError(null);
    showToast(`Uploading ${file.name}...`, 'info');

    try {
      await uploadResume(file);
      setUploadProgress('processing');
      showToast(`Upload complete. Extracting resume text...`, 'info');
      refetchStatus();
    } catch (err: any) {
      console.error(err);
      setUploadProgress('failed');
      const msg = err.response?.data?.detail || "Upload failed. Check file size (<5MB) and type (.pdf, .docx).";
      setUploadError(msg);
      showToast(msg, 'error');
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => {
    setDragOver(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const handleReprocessAction = async (id: string) => {
    setIsReprocessing(true);
    setUploadError(null);
    setUploadProgress('processing');
    showToast("Reprocessing triggered...", 'info');
    try {
      await reprocessResume(id);
      refetchStatus();
    } catch (err: any) {
      console.error(err);
      setUploadProgress('failed');
      setUploadError(err.response?.data?.detail || "Reprocessing failed.");
      showToast("Reprocessing failed.", 'error');
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleDownload = async (resumeId: string) => {
    try {
      const { url } = await getResumeDownloadUrl(resumeId);
      window.open(url, '_blank');
    } catch (err) {
      console.error(err);
      showToast("Failed to generate secure download link.", 'error');
    }
  };

  // Filter skills
  const filteredSkills = activeResume?.skills?.filter(s => 
    s.toLowerCase().includes(skillSearch.toLowerCase())
  ) || [];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Toast Alert Banner */}
      {toast && (
        <div className={`fixed top-20 right-6 z-50 flex items-center px-4 py-3 rounded-2xl shadow-lg border text-sm font-semibold transition-all duration-300 transform scale-100 ${
          toast.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
          toast.type === 'error' ? 'bg-rose-50 text-rose-800 border-rose-200' :
          'bg-indigo-50 text-indigo-800 border-indigo-200'
        }`}>
          <span>{toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️'}</span>
          <span className="ml-2">{toast.message}</span>
        </div>
      )}

      {/* Hero RAG Workspace Title Card */}
      <div className="bg-gradient-to-r from-indigo-900 via-indigo-950 to-slate-900 rounded-3xl p-6 md:p-8 text-white relative overflow-hidden shadow-md">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(99,102,241,0.15),transparent)] pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Career RAG Profile
            </span>
            <h2 className="text-3xl font-extrabold tracking-tight">
              {activeResume ? activeResume.title : 'My Career Profile'}
            </h2>
            <p className="text-sm text-indigo-200 max-w-xl leading-relaxed">
              Upload your resume in PDF or Word format. The AI parser will automatically index your profile, extract skills/projects, and calculate semantic similarity against incoming jobs in real-time.
            </p>
          </div>
          {activeResume && (
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10 space-y-1 text-xs self-start md:self-center">
              <span className="block text-indigo-300 font-bold uppercase text-[10px]">Active Profile Version</span>
              <p className="font-mono font-bold text-sm">Version {activeResume.is_active ? 'Active' : 'Archived'}</p>
              <p className="text-white/60">Extracted {new Date(activeResume.created_at).toLocaleDateString()}</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Panel: Upload & Control Center (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* File Dropzone */}
          <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-xs space-y-4">
            <h3 className="text-md font-bold text-gray-800">Upload Resume</h3>
            
            <div 
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              className={`relative border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
                dragOver ? 'border-indigo-500 bg-indigo-50/40' : 'border-gray-250 hover:border-indigo-400 bg-gray-50/50'
              }`}
            >
              <input 
                type="file" 
                accept=".pdf,.docx"
                onChange={onFileChange}
                disabled={uploadProgress === 'uploading' || uploadProgress === 'processing'}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
              />
              <div className="w-12 h-12 bg-white rounded-xl shadow-xs border border-gray-150 flex items-center justify-center text-xl mb-3">
                {uploadProgress === 'uploading' ? '📤' : uploadProgress === 'processing' ? '⚙️' : '📄'}
              </div>
              <p className="text-sm font-semibold text-gray-800">
                {uploadProgress === 'uploading' ? 'Uploading document...' :
                 uploadProgress === 'processing' ? 'AI Text Extraction & Parsing...' :
                 'Drag and drop resume here'}
              </p>
              <p className="text-xs text-gray-400 mt-1">Accepts PDF or Word (.docx) up to 5MB</p>
            </div>

            {/* Upload/Processing Details */}
            {latestFile && (
              <div className="bg-gray-50 border border-gray-200/80 rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-bold text-gray-800 truncate max-w-[200px]">{latestFile.filename}</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] uppercase font-extrabold tracking-wider ${
                    latestFile.processing_status === 'complete' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                    latestFile.processing_status === 'failed' ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                    'bg-amber-100 text-amber-800 animate-pulse border border-amber-200'
                  }`}>
                    {latestFile.processing_status}
                  </span>
                </div>

                <div className="text-[11px] text-gray-500 space-y-1 font-medium">
                  <p>Uploaded: {new Date(latestFile.uploaded_at).toLocaleString()}</p>
                  <p>Size: {(latestFile.size_bytes / 1024).toFixed(1)} KB</p>
                  {latestFile.processed_at && (
                    <p>Processed: {new Date(latestFile.processed_at).toLocaleString()}</p>
                  )}
                </div>

                {uploadError && (
                  <div className="text-xs text-rose-700 bg-rose-50 border border-rose-150 p-3 rounded-xl leading-relaxed">
                    <strong>Parsing Error:</strong> {uploadError}
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1 border-t border-gray-150">
                  {latestFile.resume_id && (
                    <button
                      onClick={() => handleDownload(latestFile.resume_id!)}
                      className="flex-1 py-2 bg-gray-100 hover:bg-gray-250 text-gray-700 font-bold rounded-xl text-xs transition-colors cursor-pointer text-center"
                    >
                      📥 Download PDF
                    </button>
                  )}
                  {latestFile.processing_status === 'failed' && (
                    <button
                      disabled={isReprocessing}
                      onClick={() => handleReprocessAction(latestFile.id)}
                      className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isReprocessing ? 'Reprocessing...' : '🔁 Reprocess File'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Parsed RAG Results (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {activeResume ? (
            <div className="bg-white rounded-3xl border border-gray-200 p-6 shadow-xs space-y-6">
              
              {/* RAG Profile Meta Details */}
              <div className="flex items-center justify-between pb-4 border-b border-gray-150">
                <h3 className="text-lg font-bold text-gray-800">Extracted RAG Summary</h3>
                <button
                  onClick={() => setShowRawText(!showRawText)}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-bold transition-colors cursor-pointer"
                >
                  {showRawText ? 'Hide Raw text' : 'Inspect Raw text'}
                </button>
              </div>

              {/* Title & Exp cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-gray-50 border border-gray-200/60 rounded-2xl p-4 space-y-1">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">AI Extracted Role</span>
                  <p className="text-md font-bold text-gray-800">{activeResume.title || 'N/A'}</p>
                </div>
                <div className="bg-gray-50 border border-gray-200/60 rounded-2xl p-4 space-y-1">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Years of Experience</span>
                  <p className="text-md font-bold text-gray-800">
                    {activeResume.years_experience !== undefined ? `${activeResume.years_experience} Years` : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Skills Filter & Tags */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <span className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                    Skills Index ({activeResume.skills?.length || 0})
                  </span>
                  <input
                    type="text"
                    value={skillSearch}
                    onChange={(e) => setSkillSearch(e.target.value)}
                    placeholder="Search parsed skills..."
                    className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs max-w-xs focus:bg-white focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {filteredSkills.length > 0 ? (
                    filteredSkills.map((skill, index) => (
                      <span 
                        key={index}
                        className="bg-indigo-50 text-indigo-700 border border-indigo-100 px-3 py-1 rounded-xl text-xs font-semibold hover:bg-indigo-100 hover:text-indigo-800 transition-colors"
                      >
                        {skill}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-gray-400 italic">No matching parsed skills found.</span>
                  )}
                </div>
              </div>

              {/* Projects list */}
              {activeResume.projects?.length > 0 && (
                <div className="space-y-4">
                  <span className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                    Extracted Projects & Portfolio
                  </span>
                  <div className="space-y-3">
                    {activeResume.projects.map((proj, idx) => (
                      <div key={idx} className="border border-gray-150 rounded-2xl p-4 bg-gray-50/40 space-y-2 hover:border-gray-350 transition-colors">
                        <div className="flex items-center justify-between font-bold text-gray-800 text-sm">
                          <span>{proj.title}</span>
                        </div>
                        {proj.description && (
                          <p className="text-xs text-gray-500 leading-relaxed font-medium">{proj.description}</p>
                        )}
                        {proj.technologies?.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {proj.technologies.map((tech, tIdx) => (
                              <span key={tIdx} className="bg-gray-100 text-gray-650 px-2 py-0.5 rounded-lg text-[10px] font-semibold border border-gray-200/50">
                                {tech}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw Text Box */}
              {showRawText && (
                <div className="space-y-2 pt-4 border-t border-gray-150">
                  <span className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Raw Extracted Document Text</span>
                  <pre className="bg-slate-900 border border-slate-950 text-[11px] text-slate-300 rounded-2xl p-4 overflow-x-auto whitespace-pre-wrap max-h-[350px] leading-relaxed font-mono">
                    {activeResume.raw_text}
                  </pre>
                </div>
              )}

            </div>
          ) : (
            <div className="bg-white rounded-3xl border border-gray-250 p-12 text-center shadow-xs">
              <div className="text-4xl mb-3">📂</div>
              <p className="text-sm font-bold text-gray-800">No active RAG profile loaded.</p>
              <p className="text-xs text-gray-400 max-w-xs mx-auto mt-1 leading-normal">
                Upload a resume in the left panel to populate your skills, titles, and match parameters automatically.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
