import React from 'react';
import type { ScoredPosting } from '../types';
import { PostingCard } from './PostingCard';
import { PostingListSkeleton } from './SkeletonLoader';
import { ErrorBanner } from './ErrorBanner';
import { EmptyState } from './EmptyState';

interface PostingListProps {
  postings: ScoredPosting[];
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  onRetry?: () => void;
  selectedPosting: ScoredPosting | null;
  onSelectPosting: (posting: ScoredPosting) => void;
  isGeneratingReport?: boolean;
}

export const PostingList: React.FC<PostingListProps> = ({
  postings,
  isLoading,
  isError,
  error,
  onRetry,
  selectedPosting,
  onSelectPosting,
  isGeneratingReport = false,
}) => {
  if (isLoading) {
    return <PostingListSkeleton />;
  }

  if (isError) {
    return (
      <ErrorBanner
        title="Backend Unavailable"
        message={error?.message || 'Unable to connect to backend. Please check that the FastAPI server is running on localhost:8000.'}
        onRetry={onRetry}
      />
    );
  }

  if (postings.length === 0) {
    return <EmptyState type="list" />;
  }

  return (
    <div className="space-y-3.5 max-h-[800px] overflow-y-auto pr-1">
      {postings.map((scoredPosting) => {
        const isSelected = selectedPosting?.posting.id === scoredPosting.posting.id;
        return (
          <PostingCard
            key={scoredPosting.posting.id || scoredPosting.posting.title}
            scoredPosting={scoredPosting}
            isSelected={isSelected}
            onSelect={onSelectPosting}
            disabled={isGeneratingReport && isSelected}
          />
        );
      })}
    </div>
  );
};
