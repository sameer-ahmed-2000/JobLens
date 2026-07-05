import React from 'react';

export const PostingListSkeleton: React.FC = () => {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="bg-white p-5 rounded-xl border border-gray-200 shadow-2xs animate-pulse">
          <div className="flex justify-between items-start mb-3">
            <div className="space-y-2 flex-1">
              <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              <div className="h-3 bg-gray-100 rounded w-1/3"></div>
            </div>
            <div className="h-6 w-12 bg-gray-200 rounded-lg"></div>
          </div>
          <div className="flex gap-2 my-3">
            <div className="h-5 w-16 bg-gray-100 rounded"></div>
            <div className="h-5 w-20 bg-gray-100 rounded"></div>
            <div className="h-5 w-14 bg-gray-100 rounded"></div>
          </div>
          <div className="h-10 bg-gray-100 rounded-lg w-full mb-2"></div>
        </div>
      ))}
    </div>
  );
};

export const GapReportSkeleton: React.FC = () => {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6 animate-pulse">
      {/* Header */}
      <div className="border-b border-gray-100 pb-4 space-y-2">
        <div className="h-6 bg-gray-200 rounded w-1/2"></div>
        <div className="h-4 bg-gray-100 rounded w-1/4"></div>
      </div>

      {/* Confidence Card Skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 p-4 rounded-xl border border-gray-100">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-1">
            <div className="h-3 bg-gray-200 rounded w-16"></div>
            <div className="h-6 bg-gray-300 rounded w-12"></div>
          </div>
        ))}
      </div>

      {/* AI Fit Summary Skeleton */}
      <div className="space-y-2">
        <div className="h-4 bg-gray-200 rounded w-32"></div>
        <div className="h-16 bg-gray-100 rounded-xl w-full"></div>
      </div>

      {/* Grouped Skills Skeleton */}
      <div className="space-y-4">
        <div className="h-4 bg-gray-200 rounded w-40"></div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-8 bg-gray-100 rounded-lg"></div>
          ))}
        </div>
      </div>
    </div>
  );
};
