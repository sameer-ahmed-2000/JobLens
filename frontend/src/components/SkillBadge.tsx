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

  let borderClass = 'border-gray-800 bg-[#211F1C] text-gray-400';
  let icon = <CheckCircleIcon size={15} className="text-gray-500" />;
  let labelText = 'HAVE';
  let labelBadgeClass = 'bg-base text-gray-400 border-gray-850';

  if (classification === 'have') {
    borderClass = 'border-focus-confirm/20 bg-focus-confirm/[0.04] text-text-warm hover:border-focus-confirm/45';
    icon = <CheckCircleIcon size={15} className="text-focus-confirm shrink-0" />;
    labelText = 'HAVE';
    labelBadgeClass = 'bg-focus-confirm/10 text-focus-confirm border-focus-confirm/20';
  } else if (classification === 'partial') {
    borderClass = 'border-signal-amber/20 bg-signal-amber/[0.04] text-text-warm hover:border-signal-amber/45';
    icon = <AlertTriangleIcon size={15} className="text-signal-amber shrink-0" />;
    labelText = 'PARTIAL';
    labelBadgeClass = 'bg-signal-amber/10 text-signal-amber border-signal-amber/20';
  } else if (classification === 'missing') {
    borderClass = 'border-alert-red/20 bg-alert-red/[0.04] text-text-warm hover:border-alert-red/45';
    icon = <XCircleIcon size={15} className="text-alert-red shrink-0" />;
    labelText = 'MISSING';
    labelBadgeClass = 'bg-alert-red/10 text-alert-red border-alert-red/20';
  }

  return (
    <div className={`rounded-xl border p-3.5 transition-all duration-150 ${borderClass} font-body shadow-sm`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2 min-w-0">
          {icon}
          <span className="font-bold text-sm truncate text-text-warm">{skill}</span>
        </div>
        
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-md border font-mono ${labelBadgeClass}`}>
            {labelText}
          </span>
          {hasBridge && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 rounded-md hover:bg-base/60 text-gray-400 hover:text-text-warm transition-colors cursor-pointer focus:outline-none"
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
          className={`mt-2.5 pt-2.5 border-t border-gray-850 text-xs leading-relaxed text-gray-400 ${
            isExpanded || classification !== 'have' ? 'block' : 'hidden sm:block'
          }`}
        >
          <div className="flex items-start gap-1.5 font-bold text-gray-300 mb-1 font-mono text-[10px]">
            <SparklesIcon size={13} className="mt-0.5 text-focus-confirm shrink-0" />
            <span>INTERVIEW BRIDGE & PREPARATION:</span>
          </div>
          <p className="pl-5 text-gray-400">{bridgeText}</p>
        </div>
      )}
    </div>
  );
};
