import React from 'react';
import type { Application } from '../types';
import { StatusBadge } from './StatusBadge';
import { BuildingIcon } from './icons';
import { ApertureRing } from './ApertureRing';

interface ApplicationCardProps {
  application: Application;
  isSelected: boolean;
  onClick: () => void;
  onDragStart?: (e: React.DragEvent<HTMLDivElement>) => void;
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({ application, isSelected, onClick, onDragStart }) => {
  const dateStr = new Date(application.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

  return (
    <div
      onClick={onClick}
      draggable={!!onDragStart}
      onDragStart={onDragStart}
      className={`viewfinder-bracket-container p-4 rounded-xl border text-left transition-all duration-150 cursor-pointer shadow-md relative ${
        isSelected
          ? 'viewfinder-active bg-surface border-gray-800'
          : 'bg-surface border-gray-850 hover:border-gray-800 hover:shadow-lg'
      }`}
    >
      {/* Corner bracket layout sub-element */}
      <div className="viewfinder-bracket-sub" />

      {/* Header */}
      <div className="flex justify-between items-start gap-2 mb-2">
        <h4 className="text-sm font-bold text-text-warm leading-tight line-clamp-2 transition-colors">
          {application.job_title}
        </h4>
        <StatusBadge status={application.status} className="shrink-0" />
      </div>

      {/* Company info */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400 font-medium mb-3 font-mono">
        <BuildingIcon size={14} className="text-gray-500 shrink-0" />
        <span className="truncate">{application.company.toUpperCase()}</span>
      </div>

      {/* Footer statistics */}
      <div className="flex items-center justify-between text-[11px] font-semibold border-t border-gray-850 pt-3">
        <div className="flex gap-2">
          {application.match_score ? (
            <div className="flex items-center gap-1.5">
              <ApertureRing score={application.match_score} size="mini" />
              <span className="text-[9px] text-gray-500 font-bold font-mono">MATCH</span>
            </div>
          ) : (
            <span className="text-gray-550 font-mono text-[9px]">NO SCORE</span>
          )}
        </div>
        <span className="text-gray-500 font-mono">UPD: {dateStr.toUpperCase()}</span>
      </div>
    </div>
  );
};
