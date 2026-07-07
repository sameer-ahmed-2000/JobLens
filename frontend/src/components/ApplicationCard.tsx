import React from 'react';
import type { Application } from '../types';
import { StatusBadge } from './StatusBadge';
import { BuildingIcon } from './icons';

interface ApplicationCardProps {
  application: Application;
  isSelected: boolean;
  onClick: () => void;
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({ application, isSelected, onClick }) => {
  const dateStr = new Date(application.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border text-left transition-all duration-150 cursor-pointer shadow-xs ${
        isSelected
          ? 'bg-indigo-50/60 border-indigo-500 ring-2 ring-indigo-500/20'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
    >
      <div className="flex justify-between items-start gap-2 mb-2">
        <h4 className="text-sm font-bold text-gray-900 leading-tight line-clamp-2 group-hover:text-indigo-600 transition-colors">
          {application.job_title}
        </h4>
        <StatusBadge status={application.status} className="shrink-0" />
      </div>

      <div className="flex items-center gap-1.5 text-xs text-gray-600 font-medium mb-3">
        <BuildingIcon size={14} className="text-gray-400 shrink-0" />
        <span className="truncate">{application.company}</span>
      </div>

      <div className="flex items-center justify-between text-[11px] font-semibold border-t border-gray-100 pt-3">
        <div className="flex gap-2">
          {application.match_score ? (
            <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
              {application.match_score}% Match
            </span>
          ) : (
            <span className="text-gray-400">No score</span>
          )}
        </div>
        <span className="text-gray-400">Upd {dateStr}</span>
      </div>
    </div>
  );
};
