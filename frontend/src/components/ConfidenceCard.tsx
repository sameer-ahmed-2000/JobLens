import React from 'react';
import type { GapReport } from '../types';
import { formatPercentage, getScoreValue } from '../utils/helpers';
import { AwardIcon, CheckCircleIcon, AlertTriangleIcon } from './icons';
import { ApertureRing } from './ApertureRing';

interface ConfidenceCardProps {
  report: GapReport;
}

export const ConfidenceCard: React.FC<ConfidenceCardProps> = ({ report }) => {
  const overallFit = formatPercentage(report.match_score || report.confidence_score);
  const scoreVal = getScoreValue(report.match_score || report.confidence_score);
  
  const gaps = report.gaps || [];
  const totalSkills = gaps.length;
  const matchedSkills = gaps.filter(
    (g) => g.classification === 'have' || g.classification === 'partial'
  ).length;
  
  const missingSkills = gaps.filter((g) => g.classification === 'missing');
  const primaryMissing = missingSkills.length > 0 ? missingSkills[0].skill : 'None';

  let priorityText = 'REVIEW';
  let priorityBadge = 'bg-signal-amber/15 text-signal-amber border-signal-amber/25';
  if (scoreVal >= 80) {
    priorityText = 'HIGH FOCUS';
    priorityBadge = 'bg-focus-confirm/15 text-focus-confirm border-focus-confirm/25';
  } else if (scoreVal >= 70) {
    priorityText = 'MID FOCUS';
    priorityBadge = 'bg-focus-confirm/10 text-focus-confirm/80 border-focus-confirm/20';
  }

  return (
    <div className="bg-gradient-to-br from-[#1E1C1A] via-[#2D2A26] to-[#1E1C1A] rounded-2xl p-5 text-text-warm shadow-md border border-gray-800 my-4 font-body">
      
      {/* Title block */}
      <div className="flex items-center justify-between mb-4 border-b border-gray-850 pb-3">
        <div className="flex items-center space-x-2">
          <AwardIcon size={18} className="text-focus-confirm" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-gray-400 font-mono">
            AI Fit Assessment & Lens Focus
          </h4>
        </div>
        <span className="text-[10px] font-bold bg-focus-confirm/10 text-focus-confirm border border-focus-confirm/25 px-2.5 py-0.5 rounded-full font-mono">
          RESOLVED SIGNAL
        </span>
      </div>

      {/* Grid readouts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
        
        {/* Overall Fit */}
        <div className="bg-base/40 p-3 rounded-xl border border-gray-850 flex items-center justify-between gap-1.5">
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase mb-1">
              OVERALL
            </p>
            <p className="text-xl font-bold text-text-warm">
              {overallFit}
            </p>
          </div>
          <ApertureRing score={scoreVal} size="mini" className="scale-105" />
        </div>

        {/* Matched Ratio */}
        <div className="bg-base/40 p-3 rounded-xl border border-gray-850">
          <p className="text-[10px] font-bold text-gray-500 uppercase mb-1">
            MATCHED
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <CheckCircleIcon size={14} className="text-focus-confirm" />
            <p className="text-lg font-bold text-text-warm">
              {totalSkills > 0 ? `${matchedSkills}/${totalSkills}` : 'N/A'}
            </p>
          </div>
        </div>

        {/* Missing Highlight */}
        <div className="bg-base/40 p-3 rounded-xl border border-gray-850">
          <p className="text-[10px] font-bold text-gray-500 uppercase mb-1">
            TOP GAP
          </p>
          <div className="flex items-center gap-1.5 mt-0.5 truncate">
            {missingSkills.length > 0 ? (
              <AlertTriangleIcon size={14} className="text-alert-red shrink-0" />
            ) : (
              <CheckCircleIcon size={14} className="text-focus-confirm shrink-0" />
            )}
            <p className="text-xs font-bold text-text-warm truncate" title={primaryMissing}>
              {primaryMissing.toUpperCase()}
            </p>
          </div>
        </div>

        {/* Priority */}
        <div className="bg-base/40 p-3 rounded-xl border border-gray-850 flex flex-col justify-between">
          <p className="text-[10px] font-bold text-gray-500 uppercase mb-1">
            PRIORITY
          </p>
          <div className="mt-0.5">
            <span className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-bold border ${priorityBadge}`}>
              {priorityText}
            </span>
          </div>
        </div>

      </div>

      {report.confidence_reasoning && (
        <div className="mt-3.5 pt-3 border-t border-gray-850 text-xs text-gray-400 leading-relaxed italic">
          "{report.confidence_reasoning}"
        </div>
      )}
    </div>
  );
};
