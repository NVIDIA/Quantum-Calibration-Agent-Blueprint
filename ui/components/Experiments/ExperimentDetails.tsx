/*
 * SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { ExperimentResult } from '@/types/qcal';

// @ts-ignore - react-plotly.js types are incomplete
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false }) as any;

interface ExperimentDetailsProps {
  experiment: ExperimentResult | null;
  loading?: boolean;
  error?: string;
  compact?: boolean; // For embedded chat view
}

export const ExperimentDetails: React.FC<ExperimentDetailsProps> = ({
  experiment,
  loading,
  error,
  compact = false
}) => {
  const [selectedPlotIndex, setSelectedPlotIndex] = useState(0);
  // Default to 'plots' tab in compact mode (chat embed), 'info' otherwise
  const [activeTab, setActiveTab] = useState<string>(compact ? 'plots' : 'info');
  const [logsContent, setLogsContent] = useState<string>('');
  const [logsAutoScroll, setLogsAutoScroll] = useState(true);
  const logsRef = useRef<HTMLPreElement>(null);

  const fetchLogs = useCallback(async (experimentId: string) => {
    try {
      const response = await fetch(`/api/history/${encodeURIComponent(experimentId)}/logs?lines=200`);
      if (!response.ok) return;
      const data = await response.json();
      setLogsContent(data.logs || 'No output logs available');
      if (logsAutoScroll && logsRef.current) {
        logsRef.current.scrollTop = logsRef.current.scrollHeight;
      }
    } catch {
      setLogsContent('Failed to load output logs');
    }
  }, [logsAutoScroll]);

  // Fetch logs when experiment changes or tab is active
  useEffect(() => {
    if (experiment?.id && activeTab === 'output') {
      fetchLogs(experiment.id);
      // Poll for updates every 2 seconds
      const interval = setInterval(() => fetchLogs(experiment.id), 2000);
      return () => clearInterval(interval);
    }
  }, [experiment?.id, activeTab, fetchLogs]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-600 dark:text-gray-400">Loading experiment details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
          Error: {error}
        </div>
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400">Select an experiment to view details</div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const statusColors: Record<string, string> = {
      success: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
      failed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
      default: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
    };

    const colorClass = statusColors[status] || statusColors.default;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
        {status}
      </span>
    );
  };

  const renderParameters = () => {
    if (!experiment.params || Object.keys(experiment.params).length === 0) {
      return <div className="text-gray-500 dark:text-gray-400">No parameters available</div>;
    }

    return (
      <div className="space-y-2">
        {Object.entries(experiment.params).map(([key, value]) => (
          <div key={key} className="flex justify-between py-1 border-b border-gray-100 dark:border-gray-700">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{key}:</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const renderResults = () => {
    if (!experiment.results || Object.keys(experiment.results).length === 0) {
      return <div className="text-gray-500 dark:text-gray-400">No results available</div>;
    }

    return (
      <div className="space-y-2">
        {Object.entries(experiment.results).map(([key, value]) => (
          <div key={key} className="border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">{key}</div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {typeof value === 'object'
                ? <pre className="bg-gray-50 dark:bg-gray-800 p-1 rounded overflow-x-auto">{JSON.stringify(value, null, 2)}</pre>
                : String(value)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderArrays = () => {
    if (!experiment.arrays || Object.keys(experiment.arrays).length === 0) {
      return <div className="text-gray-500 dark:text-gray-400">No arrays available</div>;
    }

    return (
      <div className="space-y-2">
        {Object.entries(experiment.arrays).map(([key, value]) => (
          <div key={key} className="border-b border-gray-100 dark:border-gray-700 pb-2">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300">{key}</div>
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Length: {Array.isArray(value) ? value.length : 0} elements
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-300 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold flex items-center text-gray-900 dark:text-gray-100">
              {experiment.type}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              ID: {experiment.id}
            </p>
          </div>
          <div>{getStatusBadge(experiment.status)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-gray-50 dark:bg-[#2a2b32] border-b border-gray-300 dark:border-gray-700">
        <button
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'info'
              ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          onClick={() => setActiveTab('info')}
        >
          Info
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'params'
              ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          onClick={() => setActiveTab('params')}
        >
          Parameters
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'results'
              ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          onClick={() => setActiveTab('results')}
        >
          Results
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'arrays'
              ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          onClick={() => setActiveTab('arrays')}
        >
          Arrays
        </button>
        {experiment.plots && experiment.plots.length > 0 && (
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === 'plots'
                ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
            onClick={() => setActiveTab('plots')}
          >
            Plots ({experiment.plots.length})
          </button>
        )}
        <button
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'output'
              ? 'bg-white dark:bg-[#343541] border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
          }`}
          onClick={() => setActiveTab('output')}
        >
          Output
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'info' && (
          <div className="space-y-4">
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Experiment Type:</span>
              <div className="text-gray-900 dark:text-gray-100 mt-1">{experiment.type}</div>
            </div>

            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Status:</span>
              <div className="mt-1">{getStatusBadge(experiment.status)}</div>
            </div>

            {experiment.target && (
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Target:</span>
                <div className="text-gray-900 dark:text-gray-100 mt-1">{experiment.target}</div>
              </div>
            )}

            {experiment.timestamp && (
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Timestamp:</span>
                <div className="text-gray-900 dark:text-gray-100 mt-1">
                  {new Date(experiment.timestamp).toLocaleString()}
                </div>
              </div>
            )}

            {experiment.notes && (
              <div>
                <span className="font-medium text-gray-700 dark:text-gray-300">Notes:</span>
                <div className="text-gray-900 dark:text-gray-100 mt-1">{experiment.notes}</div>
              </div>
            )}

            <div>
              <span className="font-medium text-gray-700 dark:text-gray-300">Plots:</span>
              <div className="text-gray-900 dark:text-gray-100 mt-1">{experiment.plots?.length || 0}</div>
            </div>
          </div>
        )}

        {activeTab === 'params' && renderParameters()}
        {activeTab === 'results' && renderResults()}
        {activeTab === 'arrays' && renderArrays()}
        {activeTab === 'plots' && experiment.plots && experiment.plots.length > 0 && (
          <div className="flex flex-col h-full">
            {/* Plot selector tabs */}
            {experiment.plots.length > 1 && (
              <div className="flex overflow-x-auto mb-2 border-b border-gray-200 dark:border-gray-700">
                {experiment.plots.map((plot, index) => (
                  <button
                    key={index}
                    className={`px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors ${
                      selectedPlotIndex === index
                        ? 'border-b-2 border-[#76b900] text-[#76b900]'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                    }`}
                    onClick={() => setSelectedPlotIndex(index)}
                  >
                    {plot.name || `Plot ${index + 1}`}
                  </button>
                ))}
              </div>
            )}
            {/* Plot container */}
            <div className={`flex-1 ${compact ? 'min-h-[300px]' : 'min-h-[400px]'}`}>
              {experiment.plots[selectedPlotIndex]?.data &&
               experiment.plots[selectedPlotIndex].format === 'plotly' ? (
                <Plot
                  data={experiment.plots[selectedPlotIndex].data.data || []}
                  layout={{
                    ...(experiment.plots[selectedPlotIndex].data.layout || {}),
                    autosize: true,
                    margin: { t: 40, r: 20, b: 40, l: 60 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                    font: { color: '#9ca3af' }
                  }}
                  config={{ responsive: true }}
                  style={{ width: '100%', height: '100%' }}
                  useResizeHandler
                />
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="text-gray-500 dark:text-gray-400">
                    Plot format not supported
                  </div>
                </div>
              )}
            </div>
            {/* Plot navigation footer */}
            <div className="mt-2 flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
              <span>
                Plot {selectedPlotIndex + 1} of {experiment.plots.length}
                {experiment.plots[selectedPlotIndex]?.name && ` - ${experiment.plots[selectedPlotIndex].name}`}
              </span>
              <div className="flex gap-1">
                <button
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                  onClick={() => setSelectedPlotIndex(Math.max(0, selectedPlotIndex - 1))}
                  disabled={selectedPlotIndex === 0}
                >
                  Prev
                </button>
                <button
                  className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                  onClick={() => setSelectedPlotIndex(Math.min(experiment.plots!.length - 1, selectedPlotIndex + 1))}
                  disabled={selectedPlotIndex === experiment.plots.length - 1}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'output' && (
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-800 dark:text-gray-200">Execution Output</h3>
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <input
                  type="checkbox"
                  checked={logsAutoScroll}
                  onChange={(e) => setLogsAutoScroll(e.target.checked)}
                  className="rounded"
                />
                Auto-scroll
              </label>
            </div>
            <pre
              ref={logsRef}
              className="flex-1 p-4 rounded-lg bg-gray-900 text-gray-100 text-xs font-mono overflow-auto whitespace-pre-wrap"
              style={{ minHeight: '200px' }}
            >
              {logsContent || 'No output logs available. Logs are generated during experiment execution.'}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
