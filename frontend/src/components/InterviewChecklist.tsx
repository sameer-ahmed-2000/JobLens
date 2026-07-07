import React, { useState } from 'react';

interface InterviewChecklistProps {
  applicationId: string;
}

const DEFAULT_ITEMS = [
  { id: '1', label: 'Resume sent' },
  { id: '2', label: 'Recruiter contacted' },
  { id: '3', label: 'OA completed' },
  { id: '4', label: 'Interview scheduled' },
  { id: '5', label: 'Thank-you email sent' },
];

export const InterviewChecklist: React.FC<InterviewChecklistProps> = ({ applicationId }) => {
  // In a real app, this state would persist to the backend
  // For Phase 6, we keep it client-side as per the lightweight addition request
  const storageKey = `checklist_${applicationId}`;
  
  const [checkedItems, setCheckedItems] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  const toggleItem = (id: string) => {
    const next = new Set(checkedItems);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setCheckedItems(next);
    localStorage.setItem(storageKey, JSON.stringify(Array.from(next)));
  };

  const progress = Math.round((checkedItems.size / DEFAULT_ITEMS.length) * 100);

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="p-4 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
        <h3 className="font-bold text-gray-900 text-sm">Action Checklist</h3>
        <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">
          {progress}%
        </span>
      </div>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-100 h-1">
        <div 
          className="bg-indigo-500 h-1 transition-all duration-500 ease-out" 
          style={{ width: `${progress}%` }} 
        />
      </div>

      <div className="p-3">
        {DEFAULT_ITEMS.map((item) => {
          const isChecked = checkedItems.has(item.id);
          return (
            <label 
              key={item.id} 
              className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors group"
            >
              <div className="relative flex items-center justify-center w-5 h-5">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleItem(item.id)}
                  className="peer appearance-none w-5 h-5 border-2 border-gray-300 rounded-md checked:bg-indigo-500 checked:border-indigo-500 transition-all cursor-pointer"
                />
                <svg 
                  className="absolute w-3 h-3 text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="3" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <span className={`text-sm font-medium transition-colors ${
                isChecked ? 'text-gray-400 line-through' : 'text-gray-700 group-hover:text-gray-900'
              }`}>
                {item.label}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
};
