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
          <div key={i} className="bg-white p-5 rounded-2xl border border-gray-100 shadow-xs h-24" />
        ))}
      </div>
    );
  }

  const items = [
    {
      label: 'Total Applications',
      value: metrics.applied + metrics.assessments + metrics.interviews + metrics.offers + metrics.rejected + metrics.withdrawn,
      subvalue: `${metrics.saved} saved`,
      icon: <BriefcaseIcon size={20} className="text-blue-500" />,
      bg: 'bg-blue-50',
    },
    {
      label: 'In Pipeline',
      value: metrics.assessments + metrics.interviews,
      subvalue: `${metrics.avg_days_in_pipeline} days avg`,
      icon: <TrendingUpIcon size={20} className="text-violet-500" />,
      bg: 'bg-violet-50',
    },
    {
      label: 'Success Rate',
      value: `${metrics.success_rate}%`,
      subvalue: `${metrics.offers} offers`,
      icon: <CheckCircleIcon size={20} className="text-emerald-500" />,
      bg: 'bg-emerald-50',
    },
    {
      label: 'Avg AI Match',
      value: `${metrics.average_match_score}%`,
      subvalue: `${metrics.average_confidence}% confidence`,
      icon: <AwardIcon size={20} className="text-indigo-500" />,
      bg: 'bg-indigo-50',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((item, idx) => (
        <div key={idx} className="bg-white p-5 rounded-2xl border border-gray-100 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{item.label}</p>
            <div className="mt-1 flex flex-col">
              <span className="text-2xl font-black text-gray-900">{item.value}</span>
              <span className="text-xs font-medium text-gray-400 mt-0.5">{item.subvalue}</span>
            </div>
          </div>
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${item.bg}`}>
            {item.icon}
          </div>
        </div>
      ))}
    </div>
  );
};
