import React from 'react';
import type { Application } from '../types';
import { ApplicationCard } from './ApplicationCard';

interface ApplicationColumnProps {
  title: string;
  statusColorClass: string;
  applications: Application[];
  selectedAppId?: string;
  onSelectApp: (app: Application) => void;
}

export const ApplicationColumn: React.FC<ApplicationColumnProps> = ({
  title,
  statusColorClass,
  applications,
  selectedAppId,
  onSelectApp,
}) => {
  return (
    <div className="flex flex-col h-full bg-gray-50/50 rounded-2xl border border-gray-100 w-full min-w-[280px] max-w-[320px] shrink-0">
      {/* Column Header */}
      <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-white rounded-t-2xl">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${statusColorClass.split(' ')[0]}`} />
          <h3 className="font-bold text-gray-900 text-sm tracking-wide">{title}</h3>
        </div>
        <span className="bg-gray-100 text-gray-600 text-xs font-bold px-2 py-0.5 rounded-full">
          {applications.length}
        </span>
      </div>

      {/* Column Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {applications.length === 0 ? (
          <div className="h-24 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-xl">
            <span className="text-xs font-medium text-gray-400">No applications</span>
          </div>
        ) : (
          applications.map((app) => (
            <ApplicationCard
              key={app.id}
              application={app}
              isSelected={app.id === selectedAppId}
              onClick={() => onSelectApp(app)}
            />
          ))
        )}
      </div>
    </div>
  );
};
