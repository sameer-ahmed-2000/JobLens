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
    <div className="flex flex-col h-full bg-surface/40 rounded-2xl border border-gray-850 w-full min-w-[280px] max-w-[320px] shrink-0 font-body">
      {/* Column Header */}
      <div className="p-4 border-b border-gray-850 flex justify-between items-center bg-surface rounded-t-2xl font-mono">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${statusColorClass.split(' ')[0]}`} />
          <h3 className="font-bold text-text-warm text-xs tracking-wider uppercase">{title}</h3>
        </div>
        <span className="bg-base border border-gray-800 text-gray-450 text-[10px] font-bold px-2 py-0.5 rounded-full">
          {applications.length}
        </span>
      </div>

      {/* Column Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {applications.length === 0 ? (
          <div className="h-24 flex items-center justify-center border-2 border-dashed border-gray-850 rounded-xl">
            <span className="text-xs font-semibold font-mono text-gray-550">EMPTY COLUMN</span>
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
