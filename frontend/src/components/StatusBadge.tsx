import React from 'react';
import type { ApplicationStatus } from '../types';

interface StatusBadgeProps {
  status: ApplicationStatus | string;
  className?: string;
}

export const getStatusColors = (status: string) => {
  switch (status) {
    case 'Saved':
      return 'bg-base text-gray-400 border-gray-850';
    case 'Applied':
      return 'bg-focus-confirm/10 text-focus-confirm border-focus-confirm/20';
    case 'Assessment':
    case 'Online Assessment':
      return 'bg-signal-amber/10 text-signal-amber border-signal-amber/20';
    case 'Technical Interview':
    case 'Manager Interview':
    case 'HR Interview':
      return 'bg-focus-confirm/15 text-focus-confirm border-focus-confirm/25';
    case 'Offer':
      return 'bg-focus-confirm/20 text-focus-confirm border-focus-confirm/30';
    case 'Rejected':
      return 'bg-alert-red/10 text-alert-red border-alert-red/20';
    case 'Withdrawn':
      return 'bg-base text-gray-550 border-gray-855';
    default:
      return 'bg-base text-gray-450 border-gray-850';
  }
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const colors = getStatusColors(status);
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold font-mono border uppercase ${colors} ${className}`}>
      {status}
    </span>
  );
};
