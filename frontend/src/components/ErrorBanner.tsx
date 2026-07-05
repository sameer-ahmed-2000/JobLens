import React from 'react';
import { AlertTriangleIcon, RefreshCwIcon } from './icons';

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Connection Error',
  message,
  onRetry,
}) => {
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 sm:p-5 text-rose-800 shadow-2xs my-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 mt-0.5">
          <AlertTriangleIcon size={18} />
        </div>
        <div>
          <h4 className="text-sm font-bold text-rose-900">{title}</h4>
          <p className="text-xs text-rose-700 mt-1">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white text-rose-700 border border-rose-300 rounded-lg text-xs font-bold hover:bg-rose-100 hover:border-rose-400 transition-colors shadow-2xs shrink-0 cursor-pointer focus:outline-none"
        >
          <RefreshCwIcon size={14} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
};
