import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { Application } from '../types';
import { getApplications, getDashboardMetrics, updateApplicationStatus } from '../services/api';
import { DashboardMetrics } from '../components/DashboardMetrics';
import { ApplicationBoard } from '../components/ApplicationBoard';
import { ApplicationDrawer } from '../components/ApplicationDrawer';
import { EmptyWorkspace } from '../components/EmptyWorkspace';
import { SparklesIcon } from '../components/icons';

import { useAuthToken } from '../hooks/useAuthToken';

const CareerWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);

  const token = useAuthToken();
  const isAuthenticated = !!token;

  const updateStatusMutation = useMutation({
    mutationFn: ({ appId, status }: { appId: string; status: any }) =>
      updateApplicationStatus(appId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard_metrics'] });
    },
  });

  const handleDropApp = (appId: string, status: string) => {
    updateStatusMutation.mutate({ appId, status });
  };

  // Fetch applications
  const { 
    data: applications = [], 
    isLoading: appsLoading 
  } = useQuery({
    queryKey: ['applications', token],
    queryFn: getApplications,
    enabled: isAuthenticated,
  });

  // Fetch metrics
  const { 
    data: metrics, 
    isLoading: metricsLoading 
  } = useQuery({
    queryKey: ['dashboard_metrics', token],
    queryFn: getDashboardMetrics,
    enabled: isAuthenticated,
  });


  if (!isAuthenticated) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 text-center">
        <div className="bg-surface border border-gray-800 rounded-3xl p-10 shadow-2xl space-y-6">
          <div className="w-16 h-16 bg-focus-confirm/10 border border-focus-confirm/30 rounded-2xl flex items-center justify-center mx-auto text-focus-confirm shadow-inner">
            <SparklesIcon size={36} className="animate-pulse" />
          </div>
          <div className="space-y-3">
            <h2 className="text-3xl font-extrabold text-text-warm font-display tracking-tight">
              Application Workspace
            </h2>
            <p className="text-gray-400 text-sm max-w-md mx-auto leading-relaxed">
              Track your saved job applications, interview pipelines, and stage analytics. Please sign in to access your workspace.
            </p>
          </div>
          <button
            onClick={() => window.dispatchEvent(new CustomEvent('open-auth-modal', { detail: { tab: 'signin' } }))}
            className="px-6 py-3 bg-focus-confirm/10 hover:bg-focus-confirm/20 text-focus-confirm border border-focus-confirm/40 rounded-xl font-bold font-mono text-sm transition-all cursor-pointer shadow-md inline-flex items-center gap-2"
          >
            <SparklesIcon size={16} />
            <span>Sign In to Open Workspace</span>
          </button>
        </div>
      </div>
    );
  }


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
    <div className="space-y-8 pb-12 flex flex-col h-[calc(100vh-100px)] font-body">
      {/* Header section with page title */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-black text-text-warm font-display tracking-tight">Career Workspace</h1>
          <p className="text-xs text-gray-500 mt-1 font-mono uppercase">MANAGE YOUR APPLICATIONS AND TRACK INTERVIEW PROGRESS</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-focus-confirm/10 border border-focus-confirm/20 hover:bg-focus-confirm/20 text-focus-confirm text-xs font-bold font-mono rounded-xl shadow-xs transition-colors cursor-pointer"
        >
          <SparklesIcon size={16} className="text-focus-confirm" />
          <span>DISCOVER MORE JOBS</span>
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
          onDropApp={handleDropApp}
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
