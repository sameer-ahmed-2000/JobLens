import React from 'react';
import type { Application } from '../types';
import { getStatusColors } from './StatusBadge';
import { CheckCircleIcon } from './icons';

interface TimelineProps {
  application: Application;
}

const ALL_STATUSES = [
  'Saved',
  'Applied',
  'Assessment',
  'Interview',
  'Offer',
];

const STATUS_MAPPING: Record<string, string> = {
  'Saved': 'Saved',
  'Applied': 'Applied',
  'Assessment': 'Assessment',
  'Online Assessment': 'Assessment',
  'Technical Interview': 'Interview',
  'Manager Interview': 'Interview',
  'HR Interview': 'Interview',
  'Offer': 'Offer',
};

export const Timeline: React.FC<TimelineProps> = ({ application }) => {
  const currentMappedStatus = STATUS_MAPPING[application.status] || 'Saved';
  const currentIndex = ALL_STATUSES.indexOf(currentMappedStatus);

  const isRejectedOrWithdrawn = ['Rejected', 'Withdrawn'].includes(application.status);

  return (
    <div className="relative border-l-2 border-gray-100 ml-3 space-y-6 py-2">
      {ALL_STATUSES.map((status, index) => {
        const isPast = index < currentIndex;
        const isCurrent = index === currentIndex;
        
        // If rejected/withdrawn, we grey out future steps
        const isFuture = index > currentIndex || isRejectedOrWithdrawn;

        let dotColor = 'bg-gray-200 border-gray-200';
        let textColor = 'text-gray-400';
        let detailText = '';

        if (isPast) {
          dotColor = 'bg-indigo-600 border-indigo-600';
          textColor = 'text-gray-800 font-medium';
          detailText = 'Completed';
        } else if (isCurrent && !isRejectedOrWithdrawn) {
          const colors = getStatusColors(application.status).split(' ');
          dotColor = `${colors[0]} border-white shadow-sm ring-4 ring-indigo-50`;
          textColor = 'text-indigo-700 font-bold';
          detailText = `Current: ${application.status}`;
        } else if (isCurrent && isRejectedOrWithdrawn) {
          dotColor = 'bg-rose-500 border-white shadow-sm ring-4 ring-rose-50';
          textColor = 'text-rose-700 font-bold';
          detailText = `Closed: ${application.status}`;
        }

        return (
          <div key={status} className="relative pl-6">
            {/* Timeline Dot */}
            <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 ${dotColor} transition-all duration-300`} />
            
            <div className="flex flex-col">
              <span className={`text-sm tracking-wide ${textColor}`}>
                {status}
              </span>
              {(isPast || isCurrent) && (
                <span className="text-xs text-gray-500 mt-0.5 font-medium">
                  {detailText}
                </span>
              )}
            </div>
          </div>
        );
      })}
      
      {/* End of timeline marker if rejected/withdrawn */}
      {isRejectedOrWithdrawn && (
        <div className="relative pl-6 mt-4 opacity-70">
          <div className="absolute -left-[11px] top-1 bg-white">
            <CheckCircleIcon size={20} className="text-rose-400" />
          </div>
          <span className="text-sm font-semibold text-gray-500">
            Process ended
          </span>
        </div>
      )}
    </div>
  );
};
