import React, { useState } from 'react';
import { uploadResume, getLatestResumeStatus, reprocessResume, getResumeDownloadUrl, getActiveResume } from '../services/api';
import type { ResumeFile, ActiveResume } from '../services/api';

interface ResumeUploaderProps {
  resumeFile: ResumeFile | null;
  setResumeFile: React.Dispatch<React.SetStateAction<ResumeFile | null>>;
  activeResume: ActiveResume | null;
  setActiveResume: React.Dispatch<React.SetStateAction<ActiveResume | null>>;
}

export const ResumeUploader: React.FC<ResumeUploaderProps> = ({
  resumeFile,
  setResumeFile,
  activeResume,
  setActiveResume,
}) => {
  const [resumeUploadProgress, setResumeUploadProgress] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'failed'>('idle');
  const [resumeUploadError, setResumeUploadError] = useState<string | null>(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [showRawText, setShowRawText] = useState(false);

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setResumeUploadProgress('uploading');
    setResumeUploadError(null);

    try {
      await uploadResume(file);
      setResumeUploadProgress('processing');

      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const status = await getLatestResumeStatus();
          if (status) {
            setResumeFile(status);
            if (status.processing_status === 'complete') {
              setResumeUploadProgress('complete');
              getActiveResume().then(setActiveResume).catch(console.error);
              clearInterval(interval);
            } else if (status.processing_status === 'failed') {
              setResumeUploadProgress('failed');
              setResumeUploadError(status.error_message || 'Processing failed.');
              clearInterval(interval);
            }
          }
          if (attempts > 30) {
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Error polling resume status:', err);
        }
      }, 2000);
    } catch (err: any) {
      console.error('Failed to upload resume:', err);
      setResumeUploadProgress('failed');
      setResumeUploadError(err.response?.data?.detail || 'Upload failed. Verify file format & size.');
    }
  };

  const handleReprocess = async (fileId: string) => {
    setIsReprocessing(true);
    setResumeUploadError(null);
    setResumeUploadProgress('processing');
    try {
      await reprocessResume(fileId);

      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const status = await getLatestResumeStatus();
          if (status) {
            setResumeFile(status);
            if (status.processing_status === 'complete') {
              setResumeUploadProgress('complete');
              setIsReprocessing(false);
              getActiveResume().then(setActiveResume).catch(console.error);
              clearInterval(interval);
            } else if (status.processing_status === 'failed') {
              setResumeUploadProgress('failed');
              setResumeUploadError(status.error_message || 'Processing failed.');
              setIsReprocessing(false);
              clearInterval(interval);
            }
          }
          if (attempts > 30) {
            clearInterval(interval);
            setIsReprocessing(false);
          }
        } catch (err) {
          console.error('Error polling status:', err);
        }
      }, 2000);
    } catch (err: any) {
      console.error('Reprocess failed:', err);
      setResumeUploadProgress('failed');
      setResumeUploadError(err.response?.data?.detail || 'Reprocessing failed.');
      setIsReprocessing(false);
    }
  };

  const handleDownloadResume = async (resumeId: string) => {
    try {
      const { url } = await getResumeDownloadUrl(resumeId);
      window.open(url, '_blank');
    } catch (err) {
      console.error('Failed to fetch download link', err);
      alert('Could not retrieve download link.');
    }
  };

  return (
    <div className="border-t border-gray-850 pt-4 space-y-2.5 font-body">
      <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider font-mono">
        Resume Document (.pdf, .docx)
      </label>

      {resumeFile ? (
        <div className="bg-base border border-gray-850 rounded-xl p-3.5 space-y-2 text-xs">
          <div className="flex items-center justify-between font-semibold text-text-warm">
            <span className="truncate max-w-[180px]">{resumeFile.filename}</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider ${
                resumeFile.processing_status === 'complete'
                  ? 'bg-focus-confirm/10 text-focus-confirm border border-focus-confirm/20 font-mono'
                  : resumeFile.processing_status === 'failed'
                  ? 'bg-alert-red/10 text-alert-red border border-alert-red/20 font-mono'
                  : 'bg-signal-amber/10 text-signal-amber animate-pulse border border-signal-amber/20 font-mono'
              }`}
            >
              {resumeFile.processing_status}
            </span>
          </div>

          <div className="text-[11px] text-gray-400 space-y-0.5 font-mono">
            <p>Uploaded: {new Date(resumeFile.uploaded_at).toLocaleString()}</p>
            <p>Size: {(resumeFile.size_bytes / 1024).toFixed(1)} KB</p>
            {resumeFile.resume_id && <p>Linked Active Version ID: {resumeFile.resume_id.slice(0, 8)}...</p>}
          </div>

          {resumeFile.error_message && (
            <p className="text-alert-red bg-alert-red/10 border border-alert-red/20 p-2 rounded-lg text-[11px] leading-tight font-mono">
              Error: {resumeFile.error_message}
            </p>
          )}

          <div className="flex items-center gap-2 pt-1 font-mono">
            {resumeFile.resume_id && (
              <button
                type="button"
                onClick={() => handleDownloadResume(resumeFile.resume_id!)}
                className="px-2.5 py-1.5 bg-surface hover:bg-surface/80 border border-gray-800 text-gray-305 font-bold rounded-lg text-[10px] transition-colors cursor-pointer"
              >
                📥 Download Original
              </button>
            )}

            {resumeFile.processing_status === 'failed' && (
              <button
                type="button"
                disabled={isReprocessing}
                onClick={() => handleReprocess(resumeFile.id)}
                className="px-2.5 py-1.5 bg-focus-confirm/10 hover:bg-focus-confirm/20 text-focus-confirm font-bold rounded-lg text-[10px] transition-colors cursor-pointer disabled:opacity-50 border border-focus-confirm/20"
              >
                {isReprocessing ? 'Reprocessing...' : '🔁 Reprocess Document'}
              </button>
            )}
          </div>
        </div>
      ) : (
        <p className="text-[11px] text-gray-500 italic font-mono">No resume document uploaded yet.</p>
      )}

      <div className="relative border-2 border-dashed border-gray-850 rounded-xl p-4 flex flex-col items-center justify-center hover:border-focus-confirm transition-colors bg-base/50">
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={handleResumeUpload}
          disabled={resumeUploadProgress === 'uploading' || resumeUploadProgress === 'processing'}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        <div className="text-center space-y-1">
          <p className="text-xs text-gray-400 font-medium">
            {resumeUploadProgress === 'uploading'
              ? '📤 Uploading to secure storage...'
              : resumeUploadProgress === 'processing'
              ? '⚙️ Text extraction & LLM parsing...'
              : 'Drag & drop or click to upload new resume'}
          </p>
          <p className="text-[10px] text-gray-500 font-mono">PDF or DOCX up to 5MB</p>
        </div>
      </div>

      {resumeUploadError && (
        <div className="text-xs font-semibold text-alert-red bg-alert-red/10 border border-alert-red/20 p-2.5 rounded-lg font-mono">
          {resumeUploadError}
        </div>
      )}

      {/* Active Parsed Resume Profile */}
      {activeResume && (
        <div className="bg-base/30 border border-gray-850 rounded-xl p-4 space-y-3 mt-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-text-warm uppercase tracking-wider flex items-center gap-1 font-mono">
              <span>🤖</span> Parsed Resume Profile
            </h4>
            <button
              type="button"
              onClick={() => setShowRawText(!showRawText)}
              className="text-[10px] text-focus-confirm hover:text-focus-confirm/85 font-bold font-mono transition-colors cursor-pointer"
            >
              {showRawText ? 'Hide Raw Text' : 'View Raw Text'}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs font-mono">
            <div>
              <span className="block text-[10px] text-gray-500 font-bold uppercase">Extracted Title</span>
              <span className="font-semibold text-text-warm">{activeResume.title || 'N/A'}</span>
            </div>
            <div>
              <span className="block text-[10px] text-gray-500 font-bold uppercase">Experience</span>
              <span className="font-semibold text-text-warm">
                {activeResume.years_experience !== undefined ? `${activeResume.years_experience} Years` : 'N/A'}
              </span>
            </div>
          </div>

          <div>
            <span className="block text-[10px] text-gray-500 font-bold uppercase mb-1 font-mono">
              Skills ({activeResume.skills?.length || 0})
            </span>
            <div className="flex flex-wrap gap-1 max-h-[80px] overflow-y-auto pr-1">
              {activeResume.skills?.length > 0 ? (
                activeResume.skills.map((skill, index) => (
                  <span
                    key={index}
                    className="bg-focus-confirm/10 text-focus-confirm px-2 py-0.5 rounded text-[10px] font-semibold border border-focus-confirm/20 font-mono"
                  >
                    {skill}
                  </span>
                ))
              ) : (
                <span className="text-gray-500 italic text-[11px] font-mono">No skills parsed</span>
              )}
            </div>
          </div>

          {activeResume.projects?.length > 0 && (
            <div className="space-y-1">
              <span className="block text-[10px] text-gray-500 font-bold uppercase font-mono">Extracted Projects</span>
              <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                {activeResume.projects.map((proj, index) => (
                  <div key={index} className="bg-surface border border-gray-850 rounded-lg p-2 text-[11px] space-y-1 shadow-inner">
                    <div className="flex items-center justify-between font-semibold text-text-warm">
                      <span>{proj.title}</span>
                    </div>
                    {proj.description && <p className="text-gray-400 leading-normal">{proj.description}</p>}
                    {proj.technologies?.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-0.5">
                        {proj.technologies.map((tech, tIdx) => (
                          <span key={tIdx} className="bg-gray-800/50 text-gray-300 border border-gray-700 px-1.5 py-0.5 rounded-md text-[9px] font-mono">
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

          {showRawText && (
            <div className="space-y-1 pt-1 border-t border-gray-850">
              <span className="block text-[10px] text-gray-500 font-bold uppercase font-mono">Raw Extracted Text</span>
              <pre className="bg-[#131210] border border-gray-850 text-[10px] text-gray-400 rounded-lg p-2 overflow-x-auto whitespace-pre-wrap max-h-[150px] leading-tight font-mono">
                {activeResume.raw_text}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
