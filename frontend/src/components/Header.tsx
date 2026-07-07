import React from 'react';
import { NavLink } from 'react-router-dom';
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

          {/* Navigation Tabs */}
          <div className="flex items-center space-x-1 bg-gray-50 p-1 rounded-xl border border-gray-200">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `px-4 py-2 text-sm font-bold rounded-lg transition-colors ${
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
                `px-4 py-2 text-sm font-bold rounded-lg transition-colors ${
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
    </header>
  );
};
