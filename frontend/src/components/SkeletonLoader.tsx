import React from 'react';
import { ApertureRing } from './ApertureRing';
import { BuildingIcon, AwardIcon } from './icons';

export const PostingListSkeleton: React.FC = () => {
  // Realistic mock data with varying values and lengths
  const dummyPostings = [
    {
      title: 'Principal AI Engineer',
      company: 'NeuralFlow Systems',
      source: 'INTERNAL',
      lastSeen: '2h ago',
      score: 92,
      skills: ['LANGGRAPH', 'PYTORCH', 'LLM RAG'],
      rationale: 'Exceptional fit with RAG architecture experience, agentic graph systems, and vector databases.',
    },
    {
      title: 'Senior Backend Developer (Go)',
      company: 'Scylla Ledger Co',
      source: 'LINKEDIN',
      lastSeen: '1d ago',
      score: 84,
      skills: ['GOLANG', 'GRPC', 'POSTGRESQL'],
      rationale: 'Strong backend skills matching core stack. Missing minor preferred skills in Kubernetes orchestration.',
    },
    {
      title: 'Staff MLOps Architect',
      company: 'Aether Kinetics',
      source: 'INDEED',
      lastSeen: 'Yesterday',
      score: 79,
      skills: ['AWS', 'KUBERNETES', 'MLFLOW', 'TERRAFORM'],
      rationale: 'Good cloud deployment match, though experience requirements are slightly higher than parsed profile.',
    },
    {
      title: 'Frontend engineer - React',
      company: 'PixelForge Labs',
      source: 'ZIPRECRUITER',
      lastSeen: 'Just now',
      score: 71,
      skills: ['REACT', 'TYPESCRIPT', 'TAILWIND'],
      rationale: 'Meets primary frontend guidelines. Core gap identified in backend integration skills.',
    }
  ];

  return (
    <div className="space-y-3.5 select-none pointer-events-none filter blur-[5px] saturate-50 opacity-40 transition-all duration-700">
      {dummyPostings.map((p, idx) => (
        <div
          key={idx}
          className="p-5 rounded-xl border border-gray-850 bg-surface text-left relative"
        >
          {/* Top Row */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-bold text-text-warm truncate">
                {p.title}
              </h3>
              <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5 font-mono">
                <span className="flex items-center gap-1 font-medium text-gray-300">
                  <BuildingIcon size={13} className="text-gray-500" />
                  {p.company}
                </span>
                <span className="text-gray-700">•</span>
                <span className="bg-base border border-gray-800 text-gray-400 px-2 py-0.5 rounded text-[10px] font-bold">
                  {p.source}
                </span>
                <span className="text-gray-700">•</span>
                <span className="text-gray-550 text-[10px]">
                  ACT: {p.lastSeen.toUpperCase()}
                </span>
              </div>
            </div>
            {/* SVG Dummy Ring */}
            <ApertureRing score={p.score} size="normal" className="mt-0.5" />
          </div>

          {/* Skill Chips */}
          <div className="flex flex-wrap gap-1.5 my-3">
            {p.skills.map((chip, cIdx) => (
              <span
                key={cIdx}
                className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-base text-gray-300 border border-gray-850 font-mono"
              >
                {chip}
              </span>
            ))}
          </div>

          {/* Fit Rationale */}
          <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed mb-3 bg-base/40 p-2.5 rounded-lg border border-gray-850 italic">
            "{p.rationale}"
          </p>

          {/* Footer Action Bar */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-850 text-xs font-mono text-gray-550">
            <span>SELECT TO RANGE</span>
            <span>⭐ SAVE</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export const GapReportSkeleton: React.FC = () => {
  return (
    <div className="bg-surface rounded-2xl border border-gray-850 p-6 space-y-6 select-none pointer-events-none filter blur-[6px] saturate-50 opacity-40 transition-all duration-700">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-text-warm font-display">Principal AI Engineer</h2>
          <div className="flex items-center gap-1.5 text-sm text-gray-400 font-medium mt-1 font-mono">
            <BuildingIcon size={16} className="text-gray-500" />
            <span>NeuralFlow Systems</span>
            <span className="bg-base border border-gray-800 text-gray-400 px-2 py-0.5 rounded text-xs ml-1 font-bold">
              INTERNAL
            </span>
          </div>
        </div>
      </div>

      {/* Confidence Card Mock */}
      <div className="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-5 text-white border border-indigo-900/50 my-4">
        <div className="flex items-center justify-between mb-4 border-b border-indigo-800/50 pb-3">
          <div className="flex items-center space-x-2">
            <AwardIcon size={18} className="text-indigo-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-200">
              AI Fit Assessment & Confidence
            </h4>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
          <div className="bg-white/5 p-3 rounded-xl border border-white/10">
            <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">Overall Fit</p>
            <p className="text-xl font-bold">92%</p>
          </div>
          <div className="bg-white/5 p-3 rounded-xl border border-white/10">
            <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">Matched Skills</p>
            <p className="text-xl font-bold">12 / 14</p>
          </div>
          <div className="bg-white/5 p-3 rounded-xl border border-white/10">
            <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">Top Missing</p>
            <p className="text-sm font-bold truncate">Vector Search</p>
          </div>
          <div className="bg-white/5 p-3 rounded-xl border border-white/10">
            <p className="text-[11px] font-semibold text-indigo-300 uppercase mb-1">Priority</p>
            <span className="inline-block px-2 py-0.5 rounded text-[10px] bg-emerald-900/40 text-emerald-300 border border-emerald-500/20">
              High
            </span>
          </div>
        </div>
      </div>

      {/* AI Fit Narrative Summary */}
      <div className="bg-base/40 rounded-xl p-4 border border-gray-800">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
          AI Career Advisor Summary
        </p>
        <p className="text-sm text-gray-300 leading-relaxed">
          Highly compatible candidate profile. Demonstrates extensive software engineering competence with specialized focus on LLM pipelines and automated agents. Minor gaps exist in advanced vector search custom index tuning.
        </p>
      </div>

      {/* Grouped Skills Lists */}
      <div className="space-y-4 pt-2">
        <div>
          <h3 className="text-sm font-bold text-focus-confirm flex items-center gap-1.5 mb-2 font-mono">
            <span>✅ STRONG MATCHES</span>
            <span className="bg-focus-confirm/10 text-focus-confirm text-xs px-2 py-0.5 rounded-full font-extrabold border border-focus-confirm/20">
              12
            </span>
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="h-8 bg-base border border-gray-850 rounded-lg"></div>
            <div className="h-8 bg-base border border-gray-850 rounded-lg"></div>
          </div>
        </div>
      </div>

    </div>
  );
};
