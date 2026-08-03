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
      <div className="bg-surface rounded-xl border border-dashed border-gray-800 p-8 text-center my-4">
        <div className="w-12 h-12 rounded-full bg-base border border-gray-800 text-gray-400 flex items-center justify-center mx-auto mb-3">
          <SearchIcon size={22} />
        </div>
        <h4 className="text-base font-bold text-text-warm">
          {title || 'No jobs match your criteria'}
        </h4>
        <p className="text-xs text-gray-400 max-w-sm mx-auto mt-1">
          {message || 'Try adjusting your search terms, minimum match percentage, or source filter.'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-2xl border border-gray-850 shadow-md p-10 text-center flex flex-col items-center justify-center min-h-[450px]">
      <div className="w-16 h-16 rounded-2xl bg-base border border-gray-800 text-focus-confirm flex items-center justify-center mb-4 shadow-sm">
        <SparklesIcon size={32} />
      </div>
      <h3 className="text-lg font-bold text-text-warm mb-2">
        {title || 'Select a ranked job'}
      </h3>
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
        or
      </p>
      <h4 className="text-sm font-semibold text-gray-300 mb-4">
        Search for another role.
      </h4>
      <div className="bg-base border border-gray-850 rounded-xl py-3 px-5 max-w-xs text-xs text-gray-400 font-medium">
        {message || 'The AI Gap Report & Interview Bridge suggestions will automatically appear here.'}
      </div>
    </div>
  );
};

