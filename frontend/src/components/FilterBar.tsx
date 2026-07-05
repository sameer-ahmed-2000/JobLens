import React from 'react';
import type { FilterState, SortOption } from '../types';
import { FilterIcon } from './icons';

interface FilterBarProps {
  filters: FilterState;
  onChange: (newFilters: FilterState) => void;
  availableSources: string[];
  totalJobs: number;
  filteredJobsCount: number;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  availableSources,
  totalJobs,
  filteredJobsCount,
}) => {
  const handleMinMatchChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...filters, minMatch: parseFloat(e.target.value) });
  };

  const handleSourceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...filters, source: e.target.value });
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({ ...filters, sort: e.target.value as SortOption });
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-3 rounded-xl border border-gray-200 shadow-2xs">
      
      {/* Filter controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 mr-1">
          <FilterIcon size={14} className="text-indigo-600" />
          <span>Filters:</span>
        </div>

        {/* Min Match % */}
        <select
          value={filters.minMatch}
          onChange={handleMinMatchChange}
          className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 px-2.5 py-1.5 font-medium cursor-pointer"
        >
          <option value={0}>All Match %</option>
          <option value={0.7}>70%+ Match</option>
          <option value={0.8}>80%+ Match</option>
          <option value={0.9}>90%+ Match</option>
        </select>

        {/* Job Source */}
        <select
          value={filters.source}
          onChange={handleSourceChange}
          className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 px-2.5 py-1.5 font-medium cursor-pointer"
        >
          <option value="All">All Sources</option>
          {availableSources.map((src) => (
            <option key={src} value={src}>
              {src}
            </option>
          ))}
        </select>

        {/* Sort Order */}
        <select
          value={filters.sort}
          onChange={handleSortChange}
          className="bg-gray-50 border border-gray-200 text-gray-700 text-xs rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 px-2.5 py-1.5 font-medium cursor-pointer"
        >
          <option value="score_desc">Sort: Highest Score</option>
          <option value="company_asc">Sort: Company (A-Z)</option>
        </select>
      </div>

      {/* Results counter */}
      <div className="text-xs font-semibold text-gray-600 bg-gray-100 px-3 py-1.5 rounded-lg">
        Showing <span className="text-indigo-600 font-bold">{filteredJobsCount}</span> of{' '}
        <span>{totalJobs}</span> jobs
      </div>

    </div>
  );
};
