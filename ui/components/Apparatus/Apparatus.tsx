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

import { IconRefresh, IconFlask, IconFolder, IconNetwork } from '@tabler/icons-react';
import { useEffect, useState, useMemo } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

import Search from '@/components/Search';
import { ExperimentSchema } from '@/types/qcal';

import { TreeNode } from './TreeNode';
import { ExperimentDetails } from './ExperimentDetails';
import { CodeViewer } from './CodeViewer';

interface TreeNodeData {
  [key: string]: TreeNodeData | null;
}

export const Apparatus = () => {
  const [experiments, setExperiments] = useState<ExperimentSchema[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedExperiment, setSelectedExperiment] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>('');

  const [showCodeViewer, setShowCodeViewer] = useState(false);

  const fetchExperimentData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/experiment/capabilities');
      const data = await response.json();

      if (data.experiments) {
        setExperiments(data.experiments);
      } else if (data.error) {
        throw new Error(data.error);
      }

      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching experiment data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch apparatus data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperimentData();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 200);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  const buildTree = (items: string[]): TreeNodeData => {
    const tree: TreeNodeData = {};

    // Put all experiments at root level (no splitting by underscore)
    items.forEach(item => {
      tree[item] = null;
    });

    return tree;
  };

  const filterExperiments = (
    experiments: ExperimentSchema[],
    term: string
  ): ExperimentSchema[] => {
    if (!term.trim()) return experiments;

    const lowerTerm = term.toLowerCase();

    return experiments.filter(exp =>
      exp.name.toLowerCase().includes(lowerTerm) ||
      exp.description?.toLowerCase().includes(lowerTerm) ||
      exp.parameters?.some(p => p.name?.toLowerCase().includes(lowerTerm))
    );
  };

  const filteredExperiments = useMemo(
    () => filterExperiments(experiments, debouncedSearchTerm),
    [experiments, debouncedSearchTerm]
  );

  const experimentTree = useMemo(
    () => buildTree(filteredExperiments.map(exp => exp.name)),
    [filteredExperiments]
  );

  const toggleNode = (path: string) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedNodes(newExpanded);
  };

  const handleExperimentSelect = (path: string) => {
    // Path is now the experiment name directly (no splitting)
    setSelectedExperiment(path);
  };

  // No tree expansion needed since all experiments are at root level
  useEffect(() => {
    // Clear expanded nodes when searching (flat list doesn't need expansion)
  }, [debouncedSearchTerm, filteredExperiments]);

  useEffect(() => {
    if (selectedExperiment) {
      const stillVisible = filteredExperiments.find(
        exp => exp.name === selectedExperiment
      );
      if (!stillVisible) {
        setSelectedExperiment(null);
      }
    }
  }, [filteredExperiments, selectedExperiment]);

  const selectedData = experiments.find(exp => exp.name === selectedExperiment);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-[#343541] pt-3">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="bg-gray-50 dark:bg-[#202123] border-b border-gray-200 dark:border-gray-700 px-6 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-6">
              <h1 className="text-xl font-bold text-gray-800 dark:text-gray-100">
                Apparatus
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Updated: {lastUpdate.toLocaleTimeString()}
              </span>
              <button
                onClick={fetchExperimentData}
                className="p-1.5 rounded bg-blue-500 text-white hover:bg-blue-600 transition-colors disabled:opacity-50"
                disabled={loading}
              >
                <IconRefresh size={16} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        {loading && !error ? (
          <div className="flex-1 flex justify-center items-center">
            <div className="text-gray-500 dark:text-gray-400">
              <IconRefresh className="animate-spin mb-2 mx-auto" size={32} />
              <p>Loading apparatus data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex justify-center items-center p-6">
            <div className="text-center">
              <IconNetwork className="text-red-500 mx-auto mb-4" size={48} />
              <h3 className="text-lg font-semibold text-red-700 dark:text-red-300 mb-2">
                Backend not connected
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Unable to connect to the backend. Please ensure the server is running.
              </p>
              <button
                onClick={fetchExperimentData}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors flex items-center gap-2 mx-auto"
                disabled={loading}
              >
                <IconRefresh size={16} className={loading ? 'animate-spin' : ''} />
                Retry Connection
              </button>
            </div>
          </div>
        ) : (
          <PanelGroup direction="horizontal" className="flex-1">
            {/* Left Panel - Tree View */}
            <Panel defaultSize={25} minSize={15} maxSize={40}>
              <div className="h-full bg-gray-50 dark:bg-[#202123] border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-3 border-b border-gray-300 dark:border-gray-700">
                  <Search
                    placeholder="Search experiments..."
                    searchTerm={searchTerm}
                    onSearch={setSearchTerm}
                  />
                  {searchTerm && (
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      {filteredExperiments.length} of {experiments.length} experiments
                    </div>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center">
                    <IconFlask size={16} className="mr-1" />
                    Experiments
                  </h3>

                  {filteredExperiments.length > 0 ? (
                    <div className="space-y-1">
                      {Object.entries(experimentTree).map(([name, children]) => (
                        <TreeNode
                          key={name}
                          name={name}
                          path={name}
                          childNodes={children}
                          expandedNodes={expandedNodes}
                          selectedPath={selectedExperiment || null}
                          onToggle={toggleNode}
                          onSelect={handleExperimentSelect}
                        />
                      ))}
                    </div>
                  ) : searchTerm ? (
                    <div className="text-center py-12 px-4">
                      <IconFlask size={48} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        No experiments match &quot;{searchTerm}&quot;
                      </p>
                      <button
                        onClick={() => setSearchTerm('')}
                        className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                      >
                        Clear search
                      </button>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                      No experiments available
                    </div>
                  )}
                </div>
              </div>
            </Panel>

            <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 dark:hover:bg-blue-500 transition-colors cursor-col-resize" />

            {/* Center Panel - Details */}
            <Panel defaultSize={showCodeViewer ? 35 : 75} minSize={25}>
              <div className="h-full bg-white dark:bg-[#343541]">
                <ExperimentDetails
                  experimentName={selectedExperiment || ''}
                  experimentData={selectedData}
                  onViewSource={() => setShowCodeViewer(true)}
                  showViewSourceButton={!showCodeViewer && !!selectedData?.module_path}
                />
              </div>
            </Panel>

            {/* Right Panel - Code Viewer */}
            {showCodeViewer && (
              <>
                <PanelResizeHandle className="w-1 bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 dark:hover:bg-blue-500 transition-colors cursor-col-resize" />
                <Panel defaultSize={40} minSize={20} maxSize={60}>
                  <CodeViewer
                    experimentName={selectedExperiment}
                    modulePath={selectedData?.module_path}
                    onClose={() => setShowCodeViewer(false)}
                  />
                </Panel>
              </>
            )}
          </PanelGroup>
        )}
      </div>
    </div>
  );
};
