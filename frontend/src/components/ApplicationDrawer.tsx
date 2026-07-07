import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Application, ApplicationStatus, GapReport as GapReportType } from '../types';
import { updateApplicationStatus, generateGapReport } from '../services/api';
import { GapReport } from './GapReport';
import { InterviewNotes } from './InterviewNotes';
import { Timeline } from './Timeline';
import { InterviewChecklist } from './InterviewChecklist';
import { StatusBadge } from './StatusBadge';
import { XIcon, ExternalLinkIcon, BuildingIcon } from './icons';

interface ApplicationDrawerProps {
  application: Application | null;
  onClose: () => void;
}

type Tab = 'Overview' | 'Gap Report' | 'Notes' | 'Timeline';
const TABS: Tab[] = ['Overview', 'Gap Report', 'Notes', 'Timeline'];

const STATUS_OPTIONS: ApplicationStatus[] = [
  'Saved', 'Applied', 'Assessment', 'Online Assessment',
  'Technical Interview', 'Manager Interview', 'HR Interview',
  'Offer', 'Rejected', 'Withdrawn'
];

export const ApplicationDrawer: React.FC<ApplicationDrawerProps> = ({ application, onClose }) => {
  const [activeTab, setActiveTab] = useState<Tab>('Overview');
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (application) {
      setIsOpen(true);
      // Reset tab when opening a new application
      setActiveTab('Overview');
    } else {
      setIsOpen(false);
    }
  }, [application]);

  // Mutation for status updates
  const updateStatusMutation = useMutation({
    mutationFn: (status: ApplicationStatus) => updateApplicationStatus(application!.id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard_metrics'] });
    },
  });

  // Query for gap report - only fetches if we have a job_url and the tab is active
  const {
    data: gapReportData,
    isLoading: isGapLoading,
    isError: isGapError,
    error: gapError,
    refetch: refetchGap
  } = useQuery<GapReportType, Error>({
    queryKey: ['gap_report', application?.job_url || application?.job_id],
    queryFn: () => generateGapReport({ posting_url: application?.job_url || application?.job_id }),
    enabled: !!application && (activeTab === 'Gap Report' || activeTab === 'Overview'), // Only fetch when needed
    staleTime: Infinity, // Rely on backend cache, avoid unnecessary refetches
  });

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (application) {
      updateStatusMutation.mutate(e.target.value as ApplicationStatus);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setTimeout(onClose, 300); // Allow animation to finish
  };

  if (!application) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className={`fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-40 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={handleClose}
      />

      {/* Drawer */}
      <div 
        className={`fixed inset-y-0 right-0 w-full max-w-xl bg-gray-50 shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-out border-l border-gray-200 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="bg-white px-6 py-5 border-b border-gray-200 shrink-0">
          <div className="flex justify-between items-start mb-4">
            <div className="pr-8">
              <h2 className="text-xl font-black text-gray-900 leading-tight">
                {application.job_title}
              </h2>
              <div className="flex items-center gap-2 mt-1.5 text-sm text-gray-600 font-medium">
                <BuildingIcon size={16} className="text-gray-400" />
                <span>{application.company}</span>
              </div>
            </div>
            <button 
              onClick={handleClose}
              className="p-2 -m-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors focus:outline-none"
            >
              <XIcon size={20} />
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
            {/* Status Dropdown */}
            <div className="flex items-center gap-3">
              <label className="text-xs font-bold text-gray-500 uppercase tracking-wide">
                Status
              </label>
              <div className="relative">
                <select
                  value={application.status}
                  onChange={handleStatusChange}
                  disabled={updateStatusMutation.isPending}
                  className="appearance-none bg-white border border-gray-300 text-gray-900 text-sm font-semibold rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-48 p-2 pl-3 pr-8 shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {STATUS_OPTIONS.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>

            {/* Original Job Link */}
            {application.job_url && (
              <a 
                href={application.job_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
              >
                <span>Original Post</span>
                <ExternalLinkIcon size={14} />
              </a>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white border-b border-gray-200 px-6 shrink-0">
          <div className="flex space-x-6 overflow-x-auto no-scrollbar">
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-3 text-sm font-bold border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab 
                    ? 'border-indigo-600 text-indigo-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          
          {activeTab === 'Overview' && (
            <div className="space-y-6">
              {/* Quick Summary Cards */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-xs">
                  <p className="text-xs font-semibold text-gray-500 uppercase">Match Score</p>
                  <p className="text-2xl font-black text-emerald-600 mt-1">
                    {application.match_score ? `${application.match_score}%` : '--'}
                  </p>
                </div>
                <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-xs">
                  <p className="text-xs font-semibold text-gray-500 uppercase">Confidence</p>
                  <p className="text-2xl font-black text-indigo-600 mt-1">
                    {application.confidence_score ? `${application.confidence_score}%` : '--'}
                  </p>
                </div>
              </div>
              
              <InterviewChecklist applicationId={application.id} />
              
              <div className="bg-white p-5 rounded-2xl border border-gray-100 shadow-xs">
                 <h3 className="font-bold text-gray-900 mb-4">Current Progress</h3>
                 <Timeline application={application} />
              </div>
            </div>
          )}

          {activeTab === 'Gap Report' && (
            <div className="-mx-6 -mt-6 h-[calc(100%+3rem)]">
              {/* Reuse the existing GapReport component but style it for the drawer */}
              <div className="p-6 bg-white min-h-full">
                <GapReport 
                  report={gapReportData} 
                  isLoading={isGapLoading}
                  isError={isGapError}
                  error={gapError}
                  onRetry={refetchGap}
                />
              </div>
            </div>
          )}

          {activeTab === 'Notes' && (
            <InterviewNotes applicationId={application.id} />
          )}

          {activeTab === 'Timeline' && (
            <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-xs max-w-md mx-auto w-full">
              <h3 className="font-black text-xl text-gray-900 mb-6">Application Journey</h3>
              <Timeline application={application} />
            </div>
          )}

        </div>
      </div>
    </>
  );
};
