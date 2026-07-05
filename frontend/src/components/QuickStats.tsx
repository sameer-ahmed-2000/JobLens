import React from 'react';
import type { QuickStatsData } from '../types';
import { AwardIcon, BriefcaseIcon, TrendingUpIcon, AlertTriangleIcon } from './icons';

interface QuickStatsProps {
  stats: QuickStatsData;
  isLoading?: boolean;
}

export const QuickStats: React.FC<QuickStatsProps> = ({ stats, isLoading = false }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs animate-pulse">
            <div className="h-4 w-20 bg-gray-200 rounded mb-2"></div>
            <div className="h-8 w-16 bg-gray-300 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      
      {/* Top Match */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs hover:border-indigo-300 transition-all duration-150 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            Top Match
          </p>
          <p className="text-2xl sm:text-3xl font-extrabold text-indigo-600">
            {stats.topMatch}%
          </p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
          <AwardIcon size={20} />
        </div>
      </div>

      {/* Jobs Found */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs hover:border-blue-300 transition-all duration-150 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            Jobs Found
          </p>
          <p className="text-2xl sm:text-3xl font-extrabold text-gray-900">
            {stats.jobsFound}
          </p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
          <BriefcaseIcon size={20} />
        </div>
      </div>

      {/* Avg Match */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs hover:border-emerald-300 transition-all duration-150 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            Avg Match
          </p>
          <p className="text-2xl sm:text-3xl font-extrabold text-emerald-600">
            {stats.avgMatch}%
          </p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <TrendingUpIcon size={20} />
        </div>
      </div>

      {/* Missing Skills */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs hover:border-rose-300 transition-all duration-150 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            Missing Skills
          </p>
          <p className="text-2xl sm:text-3xl font-extrabold text-rose-600">
            {stats.missingSkillsCount}
          </p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
          <AlertTriangleIcon size={20} />
        </div>
      </div>

    </div>
  );
};
