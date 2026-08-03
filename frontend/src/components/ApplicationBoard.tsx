import React from 'react';
import type { Application } from '../types';
import { ApplicationColumn } from './ApplicationColumn';
import { getStatusColors } from './StatusBadge';

interface ApplicationBoardProps {
  applications: Application[];
  selectedAppId?: string;
  onSelectApp: (app: Application) => void;
  onDropApp?: (appId: string, status: string) => void;
}

const COLUMNS = [
  { id: 'Saved', title: 'Saved Jobs', statuses: ['Saved'] },
  { id: 'Applied', title: 'Applied', statuses: ['Applied'] },
  { id: 'Assessment', title: 'Assessment', statuses: ['Assessment', 'Online Assessment'] },
  { id: 'Interview', title: 'Interview', statuses: ['Technical Interview', 'Manager Interview', 'HR Interview'] },
  { id: 'Offer', title: 'Offer', statuses: ['Offer'] },
];

export const ApplicationBoard: React.FC<ApplicationBoardProps> = ({
  applications,
  selectedAppId,
  onSelectApp,
  onDropApp,
}) => {
  return (
    <div className="flex overflow-x-auto pb-4 gap-4 snap-x h-full">
      {COLUMNS.map((col) => {
        const colApps = applications.filter((app) => col.statuses.includes(app.status));
        const colorClass = getStatusColors(col.statuses[0]);

        return (
          <div key={col.id} className="snap-start h-full min-h-0">
            <ApplicationColumn
              title={col.title}
              statusColorClass={colorClass}
              applications={colApps}
              selectedAppId={selectedAppId}
              onSelectApp={onSelectApp}
              onDropApp={onDropApp ? (appId) => onDropApp(appId, col.statuses[0]) : undefined}
            />
          </div>
        );
      })}
    </div>
  );
};
