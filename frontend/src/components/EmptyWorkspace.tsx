import React from 'react';
import { BriefcaseIcon, SparklesIcon } from './icons';

interface EmptyWorkspaceProps {
  onDiscoverClick: () => void;
}

export const EmptyWorkspace: React.FC<EmptyWorkspaceProps> = ({ onDiscoverClick }) => {
  return (
    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-12 text-center max-w-2xl mx-auto my-12">
      <div className="w-20 h-20 bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-6 transform rotate-3">
        <BriefcaseIcon size={40} className="text-indigo-500 transform -rotate-3" />
      </div>
      
      <h2 className="text-2xl font-black text-gray-900 mb-3 tracking-tight">
        Your Career Workspace is Empty
      </h2>
      
      <p className="text-gray-500 mb-8 max-w-md mx-auto leading-relaxed">
        Discover jobs that match your skills, save them to your workspace, and track your interview progress all in one place.
      </p>
      
      <button
        onClick={onDiscoverClick}
        className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-md transition-all active:scale-95"
      >
        <SparklesIcon size={18} />
        <span>Discover Jobs</span>
      </button>
    </div>
  );
};
