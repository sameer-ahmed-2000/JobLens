import React from 'react';
import type { DashboardMetrics as Metrics } from '../types';
import { BriefcaseIcon, TrendingUpIcon, AwardIcon, CheckCircleIcon } from './icons';

interface DashboardMetricsProps {
  metrics: Metrics;
  isLoading?: boolean;
}

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({ metrics, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-surface p-5 rounded-2xl border border-gray-850 h-24" />
        ))}
      </div>
    );
  }

  const items = [
    {
      label: 'TOTAL APPLICATIONS',
      value: metrics.applied + metrics.assessments + metrics.interviews + metrics.offers + metrics.rejected + metrics.withdrawn,
      subvalue: `${metrics.saved} saved`,
      icon: <BriefcaseIcon size={20} className="text-gray-400" />,
      border: 'border-gray-800',
    },
    {
      label: 'IN PIPELINE',
      value: metrics.assessments + metrics.interviews,
      subvalue: `${metrics.avg_days_in_pipeline} days avg`,
      icon: <TrendingUpIcon size={20} className="text-signal-amber" />,
      border: 'border-gray-800',
    },
    {
      label: 'SUCCESS RATE',
      value: `${metrics.success_rate}%`,
      subvalue: `${metrics.offers} offers`,
      icon: <CheckCircleIcon size={20} className="text-focus-confirm" />,
      border: 'border-gray-800',
    },
    {
      label: 'AVG AI MATCH',
      value: `${metrics.average_match_score}%`,
      subvalue: `${metrics.average_confidence}% confidence`,
      icon: <AwardIcon size={20} className="text-focus-confirm" />,
      border: 'border-gray-800',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
      {items.map((item, idx) => (
        <div key={idx} className="bg-surface p-5 rounded-2xl border border-gray-850 shadow-md flex items-center justify-between">
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">{item.label}</p>
            <div className="mt-1 flex flex-col">
              <span className="text-2xl font-black text-text-warm">{item.value}</span>
              <span className="text-[10px] font-bold text-gray-500 mt-0.5">{item.subvalue.toUpperCase()}</span>
            </div>
          </div>
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 bg-base border ${item.border}`}>
            {item.icon}
          </div>
        </div>
      ))}
    </div>
  );
};
