import React, { useState } from 'react';
import type { SkillGap } from '../types';
import { CheckCircleIcon, AlertTriangleIcon, XCircleIcon, ChevronDownIcon, SparklesIcon } from './icons';

interface SkillBadgeProps {
  gap: SkillGap;
}

export const SkillBadge: React.FC<SkillBadgeProps> = ({ gap }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { skill, classification, bridge_suggestion, suggestion } = gap;
  const bridgeText = bridge_suggestion || suggestion;
  const hasBridge = Boolean(bridgeText && bridgeText.trim().length > 0);

  let bgClass = 'bg-gray-50 text-gray-800 border-gray-200';
  let icon = <CheckCircleIcon size={15} className="text-gray-500" />;
  let labelText = 'Have';

  if (classification === 'have') {
    bgClass = 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:border-emerald-300';
    icon = <CheckCircleIcon size={15} className="text-emerald-600 shrink-0" />;
    labelText = 'Have';
  } else if (classification === 'partial') {
    bgClass = 'bg-amber-50 text-amber-900 border-amber-200 hover:border-amber-300';
    icon = <AlertTriangleIcon size={15} className="text-amber-600 shrink-0" />;
    labelText = 'Partial';
  } else if (classification === 'missing') {
    bgClass = 'bg-rose-50 text-rose-900 border-rose-200 hover:border-rose-300';
    icon = <XCircleIcon size={15} className="text-rose-600 shrink-0" />;
    labelText = 'Missing';
  }

  return (
    <div className={`rounded-xl border p-3.5 transition-all duration-150 ${bgClass} shadow-2xs`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2 min-w-0">
          {icon}
          <span className="font-bold text-sm truncate">{skill}</span>
        </div>
        
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-md bg-white/80 border border-current/20">
            {labelText}
          </span>
          {hasBridge && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 rounded-md hover:bg-white/60 text-current transition-colors cursor-pointer focus:outline-none"
              title={isExpanded ? 'Hide bridge advice' : 'Show bridge advice'}
            >
              <ChevronDownIcon
                size={16}
                className={`transform transition-transform duration-150 ${isExpanded ? 'rotate-180' : ''}`}
              />
            </button>
          )}
        </div>
      </div>

      {/* Bridge Suggestion */}
      {hasBridge && (
        <div
          className={`mt-2.5 pt-2.5 border-t border-current/10 text-xs leading-relaxed ${
            isExpanded || classification !== 'have' ? 'block' : 'hidden sm:block'
          }`}
        >
          <div className="flex items-start gap-1.5 font-semibold text-current/90 mb-1">
            <SparklesIcon size={13} className="mt-0.5 shrink-0" />
            <span>Interview Bridge & Preparation:</span>
          </div>
          <p className="text-current/80 pl-5">{bridgeText}</p>
        </div>
      )}
    </div>
  );
};
