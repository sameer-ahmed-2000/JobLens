import React from 'react';
import { SparklesIcon, SearchIcon } from './icons';

interface EmptyStateProps {
  type?: 'report' | 'list';
  title?: string;
  message?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  type = 'report',
  title,
  message,
}) => {
  if (type === 'list') {
    return (
      <div className="bg-white rounded-xl border border-dashed border-gray-300 p-8 text-center my-4">
        <div className="w-12 h-12 rounded-full bg-gray-50 border border-gray-200 text-gray-400 flex items-center justify-center mx-auto mb-3">
          <SearchIcon size={22} />
        </div>
        <h4 className="text-base font-bold text-gray-800">
          {title || 'No jobs match your criteria'}
        </h4>
        <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1">
          {message || 'Try adjusting your search terms, minimum match percentage, or source filter.'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-xs p-10 text-center flex flex-col items-center justify-center min-h-[450px]">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mb-4 shadow-2xs">
        <SparklesIcon size={32} />
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-2">
        {title || 'Select a ranked job'}
      </h3>
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
        or
      </p>
      <h4 className="text-sm font-semibold text-gray-700 mb-4">
        Search for another role.
      </h4>
      <div className="bg-gray-50 border border-gray-200 rounded-xl py-3 px-5 max-w-xs text-xs text-gray-600 font-medium shadow-2xs">
        {message || 'The AI Gap Report & Interview Bridge suggestions will automatically appear here.'}
      </div>
    </div>
  );
};
