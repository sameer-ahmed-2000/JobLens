import React from 'react';
import { SparklesIcon } from './icons';

export const Header: React.FC = () => {
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

          {/* Workflow Step Indicators */}
          <div className="hidden lg:flex items-center bg-gray-50 border border-gray-200 rounded-full px-4 py-1.5 text-xs font-medium text-gray-600 shadow-2xs">
            <span className="text-indigo-600 font-semibold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Resume
            </span>
            <span className="mx-2 text-gray-300">→</span>
            <span className="text-indigo-600 font-semibold">Discover Jobs</span>
            <span className="mx-2 text-gray-300">→</span>
            <span className="text-indigo-600 font-semibold">Ranked Results</span>
            <span className="mx-2 text-gray-300">→</span>
            <span className="text-indigo-600 font-semibold">Click Job</span>
            <span className="mx-2 text-gray-300">→</span>
            <span className="bg-indigo-600 text-white px-2 py-0.5 rounded-full font-semibold">
              Gap Report
            </span>
          </div>

        </div>
      </div>
    </header>
  );
};
