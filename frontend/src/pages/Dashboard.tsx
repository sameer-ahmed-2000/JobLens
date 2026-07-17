import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import type { ScoredPosting, FilterState, SortOption, GapReport as GapReportType } from '../types';
import { getRankedPostings, generateGapReport, getMatchDetail, createStreamTicket, getMatches, QUERY_CONFIG } from '../services/api';
import { calculateQuickStats, getScoreValue } from '../utils/helpers';
import { QuickStats } from '../components/QuickStats';
import { SearchBar } from '../components/SearchBar';
import { FilterBar } from '../components/FilterBar';
import { PostingList } from '../components/PostingList';
import { GapReport } from '../components/GapReport';

const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [selectedPosting, setSelectedPosting] = useState<ScoredPosting | null>(null);
  const [searchText, setSearchText] = useState<string>('');
  const [filters, setFilters] = useState<FilterState>({
    minMatch: 0,
    source: 'All',
    sort: 'score_desc' as SortOption,
  });
  const autoSelectedRef = useRef(false);
  const [newMatchIds, setNewMatchIds] = useState<string[]>([]);

  // SSE connection setup with ticket-based auth & gap backfilling
  const lastSeenTimestampRef = useRef<string>(new Date().toISOString());
  const hasConnectedOnceRef = useRef<boolean>(false);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let isActive = true;

    const connectSSE = async () => {
      try {
        const ticket = await createStreamTicket();
        if (!isActive) return;

        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        eventSource = new EventSource(`${API_URL}/api/stream/jobs?ticket=${ticket}`);

        eventSource.onopen = () => {
          if (hasConnectedOnceRef.current) {
            console.log("SSE reconnected. Fetching missed matches since:", lastSeenTimestampRef.current);
            getMatches(lastSeenTimestampRef.current).then((missedMatches) => {
              if (!isActive) return;
              if (missedMatches && missedMatches.length > 0) {
                const missedIds = missedMatches.map(m => m.id);
                setNewMatchIds(prev => [...prev, ...missedIds]);
                setTimeout(() => {
                  setNewMatchIds(prev => prev.filter(id => !missedIds.includes(id)));
                }, 5000);

                queryClient.setQueryData<ScoredPosting[]>(['postings'], (oldPostings) => {
                  if (!oldPostings) return missedMatches;
                  const filteredMissed = missedMatches.filter(
                    m => !oldPostings.some(p => p.id === m.id || p.posting.id === m.posting.id)
                  );
                  return [...filteredMissed, ...oldPostings];
                });

                lastSeenTimestampRef.current = new Date().toISOString();
              }
            }).catch(err => {
              console.error("Failed to backfill matches on SSE reconnect:", err);
            });
          } else {
            hasConnectedOnceRef.current = true;
            console.log("SSE initial connection established.");
          }
        };

        eventSource.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.type === 'new_match') {
              const matchId = payload.job_match_id;
              
              const newMatch: ScoredPosting = {
                id: matchId,
                overall_score: payload.score,
                fit_rationale: "New live match! Click to analyze.",
                status: "new",
                posting: {
                  id: matchId,
                  title: payload.title,
                  company: payload.company,
                  url: payload.url,
                  source: payload.source || 'Live',
                  description: '',
                }
              };

              setNewMatchIds(prev => [...prev, matchId]);
              setTimeout(() => {
                setNewMatchIds(prev => prev.filter(id => id !== matchId));
              }, 5000);

              queryClient.setQueryData<ScoredPosting[]>(['postings'], (oldPostings) => {
                if (!oldPostings) return [newMatch];
                if (oldPostings.some(p => p.id === matchId || p.posting.id === newMatch.posting.id)) {
                  return oldPostings;
                }
                return [newMatch, ...oldPostings];
              });

              lastSeenTimestampRef.current = new Date().toISOString();
            }
          } catch (err) {
            console.error("Failed to parse SSE payload:", err);
          }
        };

        eventSource.onerror = (err) => {
          console.error("SSE connection error, EventSource will automatically attempt reconnection.", err);
        };
      } catch (err) {
        console.error("Failed to initialize SSE connection ticket:", err);
        setTimeout(() => {
          if (isActive) connectSSE();
        }, 5000);
      }
    };

    connectSSE();

    return () => {
      isActive = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [queryClient]);

  // Fetch ranked postings with React Query (Refinement #11: staleTime 5 mins)
  const {
    data: postings = [],
    isLoading: isPostingsLoading,
    isError: isPostingsError,
    error: postingsError,
    refetch: refetchPostings,
  } = useQuery({
    queryKey: ['postings'],
    queryFn: getRankedPostings,
    staleTime: QUERY_CONFIG.staleTime,
    refetchOnWindowFocus: QUERY_CONFIG.refetchOnWindowFocus,
  });

  // Mutation to fetch match detail (triggers lazy rationale generation)
  const fetchMatchDetailMutation = useMutation<ScoredPosting, Error, string>({
    mutationFn: (matchId) => getMatchDetail(matchId),
    onSuccess: (updatedMatch) => {
      setSelectedPosting(updatedMatch);
      queryClient.setQueryData<ScoredPosting[]>(['postings'], (oldPostings) => {
        if (!oldPostings) return [];
        return oldPostings.map((p) =>
          (p.id === updatedMatch.id || p.posting.id === updatedMatch.posting.id) ? updatedMatch : p
        );
      });
    },
  });

  // Mutation to generate Gap Report
  const generateReportMutation = useMutation<GapReportType, Error, { posting_url: string }>({
    mutationFn: (req) => generateGapReport(req),
  });

  // Auto-select match on load (supports deep linking via ?match=...)
  useEffect(() => {
    if (postings.length > 0 && !autoSelectedRef.current) {
      autoSelectedRef.current = true;
      const matchParam = searchParams.get('match');
      let targetJob = postings[0];

      if (matchParam) {
        const found = postings.find(p => p.id === matchParam || p.posting.id === matchParam);
        if (found) {
          targetJob = found;
        } else {
          // If the match isn't in the postings list (e.g. filtered out by display_threshold), load it lazily
          getMatchDetail(matchParam)
            .then((loadedMatch) => {
              setSelectedPosting(loadedMatch);
              const matchIdentifier = loadedMatch.id || loadedMatch.posting.id;
              if (matchIdentifier) {
                fetchMatchDetailMutation.mutate(matchIdentifier);
              }
              const targetIdentifier = loadedMatch.posting.url || loadedMatch.posting.id;
              if (targetIdentifier) {
                generateReportMutation.mutate({ posting_url: targetIdentifier });
              }
            })
            .catch((err) => {
              console.error("Failed to load match detail from deep-link:", err);
            });
          return;
        }
      }

      setSelectedPosting(targetJob);
      const matchIdentifier = targetJob.id || targetJob.posting.id;
      if (matchIdentifier) {
        fetchMatchDetailMutation.mutate(matchIdentifier);
      }

      const targetIdentifier = targetJob.posting.url || targetJob.posting.id;
      if (targetIdentifier) {
        generateReportMutation.mutate({ posting_url: targetIdentifier });
      }
    }
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [postings, searchParams]);

  // Handle manual selection of a job posting
  const handleSelectPosting = (posting: ScoredPosting) => {
    if (generateReportMutation.isPending && selectedPosting?.posting.id === posting.posting.id) {
      return; // Disable repeated clicks on the same active card while loading
    }
    setSelectedPosting(posting);

    const matchIdentifier = posting.id || posting.posting.id;
    if (matchIdentifier) {
      fetchMatchDetailMutation.mutate(matchIdentifier);
    }

    const targetIdentifier = posting.posting.url || posting.posting.id;
    if (targetIdentifier) {
      generateReportMutation.mutate({ posting_url: targetIdentifier });
    }
  };

  // Derive unique sources from postings for Filter dropdown
  const availableSources = useMemo(() => {
    const sourcesSet = new Set<string>();
    postings.forEach((p) => {
      if (p.posting.source && p.posting.source.trim()) {
        sourcesSet.add(p.posting.source.trim());
      }
    });
    return Array.from(sourcesSet).sort();
  }, [postings]);

  // Filter and Sort Postings (Refinement #7: search title, company, rationale, AND source)
  const filteredPostings = useMemo(() => {
    return postings
      .filter((p) => {
        // Search text matching
        if (searchText.trim()) {
          const query = searchText.toLowerCase().trim();
          const titleMatch = p.posting.title.toLowerCase().includes(query);
          const companyMatch = p.posting.company.toLowerCase().includes(query);
          const rationaleMatch = (p.fit_rationale || '').toLowerCase().includes(query);
          const sourceMatch = (p.posting.source || '').toLowerCase().includes(query);
          if (!titleMatch && !companyMatch && !rationaleMatch && !sourceMatch) {
            return false;
          }
        }

        // Minimum match percentage filtering
        if (filters.minMatch > 0) {
          const scoreVal = getScoreValue(p.overall_score);
          if (scoreVal < filters.minMatch * 100) {
            return false;
          }
        }

        // Job Source filtering
        if (filters.source !== 'All') {
          if (p.posting.source !== filters.source) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        if (filters.sort === 'score_desc') {
          return getScoreValue(b.overall_score) - getScoreValue(a.overall_score);
        }
        if (filters.sort === 'company_asc') {
          return a.posting.company.localeCompare(b.posting.company);
        }
        return 0;
      });
  }, [postings, searchText, filters]);

  // Compute Quick Stats (Refinement #2)
  const quickStats = useMemo(() => {
    return calculateQuickStats(postings, generateReportMutation.data);
  }, [postings, generateReportMutation.data]);

  return (
    <div className="space-y-6 pb-12">
      
      {/* Quick Stats Summary Cards (Refinement #2) */}
      <QuickStats stats={quickStats} isLoading={isPostingsLoading} />

      {/* Search and Filter Controls (Refinement #7) */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
        <SearchBar
          value={searchText}
          onChange={setSearchText}
          placeholder="Search jobs by title, company, LangGraph rationale, or source..."
        />
        <FilterBar
          filters={filters}
          onChange={setFilters}
          availableSources={availableSources}
          totalJobs={postings.length}
          filteredJobsCount={filteredPostings.length}
        />
      </div>

      {/* Two-Column Layout (Refinement #12: Jobs ↓ Gap Report on mobile) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Panel: Ranked Job List (5 cols on Desktop) */}
        <div className="lg:col-span-5">
          <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-xs">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-100">
              <h2 className="text-base font-extrabold text-gray-900 flex items-center gap-2">
                <span>Ranked Job Matches</span>
                <span className="bg-indigo-100 text-indigo-800 text-xs px-2 py-0.5 rounded-full font-bold">
                  {filteredPostings.length}
                </span>
              </h2>
              <span className="text-xs text-gray-400 font-medium hidden sm:inline">
                Click a card to analyze
              </span>
            </div>
            
            <PostingList
              postings={filteredPostings}
              isLoading={isPostingsLoading}
              isError={isPostingsError}
              error={postingsError as Error}
              onRetry={refetchPostings}
              selectedPosting={selectedPosting}
              onSelectPosting={handleSelectPosting}
              isGeneratingReport={generateReportMutation.isPending}
              newMatchIds={newMatchIds}
            />
          </div>
        </div>

        {/* Right Panel: Gap Report (7 cols on Desktop) */}
        <div className="lg:col-span-7 sticky top-24">
          <GapReport
            report={generateReportMutation.data}
            isLoading={generateReportMutation.isPending}
            isError={generateReportMutation.isError}
            error={generateReportMutation.error}
            selectedPosting={selectedPosting}
            onRetry={() => {
              if (selectedPosting) {
                const targetId = selectedPosting.posting.url || selectedPosting.posting.id;
                if (targetId) {
                  generateReportMutation.mutate({ posting_url: targetId });
                }
              }
            }}
          />
        </div>

      </div>

    </div>
  );
};

export default Dashboard;
