import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { Application } from '../types';
import { getApplications, getDashboardMetrics } from '../services/api';
import { DashboardMetrics } from '../components/DashboardMetrics';
import { ApplicationBoard } from '../components/ApplicationBoard';
import { ApplicationDrawer } from '../components/ApplicationDrawer';
import { EmptyWorkspace } from '../components/EmptyWorkspace';
import { SparklesIcon } from '../components/icons';

const CareerWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  // Fetch applications
  const { 
    data: applications = [], 
    isLoading: appsLoading 
  } = useQuery({
    queryKey: ['applications'],
    queryFn: getApplications,
  });

  // Fetch metrics
  const { 
    data: metrics, 
    isLoading: metricsLoading 
  } = useQuery({
    queryKey: ['dashboard_metrics'],
    queryFn: getDashboardMetrics,
  });

  if (appsLoading || metricsLoading) {
    return (
      <div className="space-y-6">
        <DashboardMetrics metrics={{} as any} isLoading={true} />
        <div className="h-[600px] bg-gray-100 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (applications.length === 0) {
    return <EmptyWorkspace onDiscoverClick={() => navigate('/')} />;
  }

  return (
    <div className="space-y-8 pb-12 flex flex-col h-[calc(100vh-100px)]">
      {/* Header section with page title */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-black text-gray-900 tracking-tight">Career Workspace</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your applications and track interview progress.</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 text-sm font-bold rounded-xl shadow-xs transition-colors"
        >
          <SparklesIcon size={16} className="text-indigo-600" />
          <span>Discover More Jobs</span>
        </button>
      </div>

      {/* Metrics Row */}
      {metrics && (
        <div className="shrink-0">
          <DashboardMetrics metrics={metrics} />
        </div>
      )}

      {/* Kanban Board */}
      <div className="flex-1 min-h-[500px] overflow-hidden -mx-4 px-4 sm:mx-0 sm:px-0">
        <ApplicationBoard
          applications={applications}
          selectedAppId={selectedApp?.id}
          onSelectApp={setSelectedApp}
        />
      </div>

      {/* Drawer */}
      <ApplicationDrawer
        application={selectedApp}
        onClose={() => setSelectedApp(null)}
      />
    </div>
  );
};

export default CareerWorkspace;
