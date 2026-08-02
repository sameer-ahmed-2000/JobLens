import React from 'react';
import type { QuickStatsData } from '../types';

interface QuickStatsProps {
  stats: QuickStatsData;
  isLoading?: boolean;
}

export const QuickStats: React.FC<QuickStatsProps> = ({ stats, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="bg-surface py-4 px-6 rounded-xl border border-gray-800 flex items-center justify-between animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex-1 text-center space-y-1">
            <div className="h-3 w-16 bg-gray-800 rounded mx-auto"></div>
            <div className="h-6 w-12 bg-gray-700 rounded mx-auto"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-gray-800 divide-x divide-gray-800 flex items-center py-3.5 px-2 shadow-md font-mono text-center">
      
      {/* Top Match */}
      <div className="flex-1">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-0.5">
          Top Match
        </p>
        <p className="text-xl sm:text-2xl font-black text-focus-confirm">
          {stats.topMatch}%
        </p>
      </div>

      {/* Jobs Found */}
      <div className="flex-1">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-0.5">
          Jobs Found
        </p>
        <p className="text-xl sm:text-2xl font-black text-text-warm">
          {stats.jobsFound}
        </p>
      </div>

      {/* Avg Match */}
      <div className="flex-1">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-0.5">
          Avg Match
        </p>
        <p className="text-xl sm:text-2xl font-black text-focus-confirm">
          {stats.avgMatch}%
        </p>
      </div>

      {/* Missing Skills */}
      <div className="flex-1">
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-0.5">
          Missing
        </p>
        <p className="text-xl sm:text-2xl font-black text-alert-red">
          {stats.missingSkillsCount}
        </p>
      </div>

    </div>
  );
};
