import React from 'react';
import type { GapReport } from '../types';
import { formatPercentage, getScoreValue } from '../utils/helpers';
import { AwardIcon, CheckCircleIcon, AlertTriangleIcon } from './icons';

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

  let priorityText = 'Review';
  let priorityBadge = 'bg-amber-100 text-amber-800 border-amber-300';
  if (scoreVal >= 80) {
    priorityText = 'High Priority';
    priorityBadge = 'bg-emerald-100 text-emerald-800 border-emerald-300';
  } else if (scoreVal >= 70) {
    priorityText = 'Medium Priority';
    priorityBadge = 'bg-indigo-100 text-indigo-800 border-indigo-300';
  }

  return (
    <div className="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-5 text-white shadow-md border border-indigo-900/50 my-4">
      <div className="flex items-center justify-between mb-4 border-b border-indigo-800/50 pb-3">
        <div className="flex items-center space-x-2">
          <AwardIcon size={18} className="text-indigo-400" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-200">
            AI Fit Assessment & Confidence
          </h4>
        </div>
        <span className="text-[11px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2.5 py-0.5 rounded-full">
          Verified Match
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        
        {/* Overall Fit */}
        <div className="bg-white/5 backdrop-blur-xs p-3 rounded-xl border border-white/10">
          <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">
            Overall Fit
          </p>
          <p className="text-xl sm:text-2xl font-black text-white">
            {overallFit}
          </p>
        </div>

        {/* Matched Ratio */}
        <div className="bg-white/5 backdrop-blur-xs p-3 rounded-xl border border-white/10">
          <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">
            Matched Skills
          </p>
          <div className="flex items-center gap-1.5">
            <CheckCircleIcon size={16} className="text-emerald-400" />
            <p className="text-xl sm:text-2xl font-black text-white">
              {totalSkills > 0 ? `${matchedSkills} / ${totalSkills}` : 'N/A'}
            </p>
          </div>
        </div>

        {/* Missing Highlight */}
        <div className="bg-white/5 backdrop-blur-xs p-3 rounded-xl border border-white/10">
          <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">
            Top Missing
          </p>
          <div className="flex items-center gap-1.5 truncate">
            {missingSkills.length > 0 ? (
              <AlertTriangleIcon size={16} className="text-rose-400 shrink-0" />
            ) : (
              <CheckCircleIcon size={16} className="text-emerald-400 shrink-0" />
            )}
            <p className="text-sm font-bold text-white truncate" title={primaryMissing}>
              {primaryMissing}
            </p>
          </div>
        </div>

        {/* Priority */}
        <div className="bg-white/5 backdrop-blur-xs p-3 rounded-xl border border-white/10 flex flex-col justify-between">
          <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">
            Demo Priority
          </p>
          <div>
            <span className={`inline-block px-2.5 py-0.5 rounded-md text-xs font-bold border ${priorityBadge}`}>
              {priorityText}
            </span>
          </div>
        </div>

      </div>

      {report.confidence_reasoning && (
        <div className="mt-3.5 pt-3 border-t border-indigo-800/40 text-xs text-indigo-200/90 leading-relaxed italic">
          "{report.confidence_reasoning}"
        </div>
      )}
    </div>
  );
};
