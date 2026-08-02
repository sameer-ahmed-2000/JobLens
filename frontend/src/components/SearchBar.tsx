import React from 'react';
import { SearchIcon, XIcon } from './icons';

interface SearchBarProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search jobs by title, company, skills, rationale, or source...'
}) => {
  return (
    <div className="relative flex-1 w-full font-body">
      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500">
        <SearchIcon size={18} />
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="block w-full pl-10 pr-10 py-2.5 bg-surface border border-gray-800 rounded-xl text-sm placeholder-gray-500 text-text-warm focus:outline-none focus:ring-1 focus:ring-focus-confirm focus:border-focus-confirm transition-all duration-150 shadow-inner"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-text-warm cursor-pointer focus:outline-none"
          title="Clear search"
        >
          <XIcon size={16} />
        </button>
      )}
    </div>
  );
};
