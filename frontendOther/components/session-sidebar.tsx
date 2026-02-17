'use client';

import { useState } from 'react';
import { useSessionStore } from '@/lib/store/session';
import { UploadPanel } from './upload-panel';

interface SessionSidebarProps {
  isCollapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
}

export function SessionSidebar({
  isCollapsed = false,
  onToggle,
}: SessionSidebarProps) {
  const [activeTab, setActiveTab] = useState<'materials' | 'settings'>('materials');
  const { currentTopic, setTopic } = useSessionStore();

  return (
    <div
      className={`flex flex-col bg-black border-l border-zinc-800 transition-all duration-300 ${
        isCollapsed ? 'w-0' : 'w-80'
      } overflow-hidden`}
    >
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-4 border-b border-zinc-800">
        <h2 className="text-lg font-bold text-white">Session</h2>
        <button
          onClick={() => onToggle?.(!isCollapsed)}
          className="p-2 hover:bg-zinc-800 rounded transition-colors text-zinc-400 hover:text-white"
          aria-label="Toggle sidebar"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      <div className="flex-shrink-0 px-4 py-3 border-b border-zinc-800">
        <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
          Current Topic
        </label>
        <input
          type="text"
          value={currentTopic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full px-3 py-2 bg-zinc-900 text-white rounded border border-zinc-700 focus:border-zinc-500 focus:outline-none text-sm"
          placeholder="e.g., Calculus"
        />
      </div>

      <div className="flex-shrink-0 flex border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('materials')}
          className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wide transition-colors ${
            activeTab === 'materials'
              ? 'text-white border-b-2 border-white'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Materials
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wide transition-colors ${
            activeTab === 'settings'
              ? 'text-white border-b-2 border-white'
              : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Settings
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'materials' && <UploadPanel />}
        {activeTab === 'settings' && <SettingsPanel />}
      </div>
    </div>
  );
}

function SettingsPanel() {
  return (
    <div className="p-4 text-sm text-white">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
            Voice Speed
          </label>
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            defaultValue="1"
            className="w-full accent-zinc-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wide mb-2">
            Difficulty Level
          </label>
          <select className="w-full px-3 py-2 bg-zinc-900 rounded border border-zinc-700 text-sm text-white">
            <option>Beginner</option>
            <option>Intermediate</option>
            <option>Advanced</option>
          </select>
        </div>
      </div>
    </div>
  );
}
