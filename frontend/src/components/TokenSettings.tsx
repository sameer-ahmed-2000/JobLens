import React, { useState } from 'react';
import { DEFAULT_USER_TOKEN } from '../constants/auth';

interface TokenSettingsProps {
  token: string;
  onSaveToken: (newToken: string) => void;
}

export const TokenSettings: React.FC<TokenSettingsProps> = ({ token, onSaveToken }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempToken, setTempToken] = useState(token);

  const handleSave = () => {
    const trimmed = tempToken.trim();
    if (trimmed) {
      onSaveToken(trimmed);
      setIsEditing(false);
    }
  };

  return (
    <div className="flex items-center space-x-2 bg-base px-3 py-1.5 rounded-xl border border-gray-800 text-xs font-mono">
      <span className="text-gray-500 font-medium">KEY:</span>
      {isEditing ? (
        <div className="flex items-center gap-1.5">
          <input
            type="password"
            value={tempToken}
            onChange={(e) => setTempToken(e.target.value)}
            placeholder="Enter API token"
            className="w-32 bg-surface border border-gray-800 text-text-warm rounded px-1.5 py-0.5 font-mono text-[11px] focus:ring-1 focus:ring-focus-confirm focus:outline-none"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
              if (e.key === 'Escape') {
                setTempToken(token);
                setIsEditing(false);
              }
            }}
          />
          <button
            onClick={handleSave}
            className="bg-focus-confirm/20 hover:bg-focus-confirm/30 text-focus-confirm font-bold px-2 py-0.5 rounded transition-colors cursor-pointer border border-focus-confirm/30"
          >
            Save
          </button>
          <button
            onClick={() => {
              setTempToken(token);
              setIsEditing(false);
            }}
            className="text-gray-500 hover:text-gray-400 transition-colors font-bold cursor-pointer"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="font-mono text-gray-455 font-semibold max-w-[120px] truncate">
            {token === DEFAULT_USER_TOKEN ? DEFAULT_USER_TOKEN : `${token.slice(0, 4)}...${token.slice(-4)}`}
          </span>
          <button
            onClick={() => setIsEditing(true)}
            className="text-focus-confirm hover:text-focus-confirm/80 font-bold hover:underline cursor-pointer"
          >
            CHANGE
          </button>
        </div>
      )}
    </div>
  );
};
