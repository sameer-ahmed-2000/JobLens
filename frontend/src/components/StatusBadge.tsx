import React from 'react';
import type { ApplicationStatus } from '../types';

interface StatusBadgeProps {
  status: ApplicationStatus | string;
  className?: string;
}

export const getStatusColors = (status: string) => {
  switch (status) {
    case 'Saved':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    case 'Applied':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'Assessment':
    case 'Online Assessment':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'Technical Interview':
    case 'Manager Interview':
    case 'HR Interview':
      return 'bg-violet-100 text-violet-800 border-violet-200';
    case 'Offer':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    case 'Rejected':
      return 'bg-rose-100 text-rose-800 border-rose-200';
    case 'Withdrawn':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200';
  }
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const colors = getStatusColors(status);
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${colors} ${className}`}>
      {status}
    </span>
  );
};
